from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from xinyu_runtime_security import bridge_source_version


DEFAULT_CORE_URL = "http://127.0.0.1:8765"
DEFAULT_QQ_GATEWAY_CONFIG = Path(__file__).resolve().with_name("xinyu_qq_gateway.config.json")


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.+)$", text)
    return match.group(1).strip() if match else default


def mask_private_identifier(value: str) -> str:
    return re.sub(r"\d{5,}", lambda m: m.group(0)[:2] + "***" + m.group(0)[-2:], value)


def redact_local_path(value: str) -> str:
    text = str(value)
    lowered = text.lower()
    if lowered.endswith("xinyu_core_bridge.py"):
        return "<xinyu_core_bridge.py>"
    if "xinyu_qq_gateway" in lowered:
        return "<xinyu_qq_gateway>"
    if "kohakuterrarium-main" in lowered and "examples" in lowered and "xinyu" in lowered:
        return "<xinyu_dir>"
    if re.search(r"(?i)([a-z]:\\|/users/|/home/|\\\\)", text):
        return "<local_path>"
    return text


def redact_core_data(data: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(data)
    for key in ("xinyu_dir", "memory_root"):
        if key in redacted:
            redacted[key] = redact_local_path(str(redacted[key]))
    return redacted


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def file_sha256(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def plugin_source_digest(path: Path) -> str:
    if not path.exists() or not path.is_dir():
        return ""
    digest = hashlib.sha256()
    for file_path in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        if not file_path.is_file() or file_path.suffix.lower() not in {".py", ".yaml", ".json"}:
            continue
        digest.update(file_path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha256(file_path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def extract_shell_version(path: Path) -> str:
    text = read_text(path)
    match = re.search(r'(?m)^SHELL_VERSION\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1).strip() if match else "unknown"


def extract_gateway_version(path: Path) -> str:
    text = read_text(path)
    match = re.search(r'(?m)^GATEWAY_VERSION\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1).strip() if match else "unknown"


def http_json(url: str, timeout: float = 3.0) -> tuple[bool, dict[str, Any] | str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            return True, data if isinstance(data, dict) else {"value": data}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return False, f"HTTP {exc.code}: {body[:160]}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def tcp_connect(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def netstat_lines(port: int) -> list[str]:
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except Exception:
        return []
    needle = f":{port}"
    return [line.strip() for line in result.stdout.splitlines() if needle in line]


def has_established_local(port: int) -> bool:
    return any("ESTABLISHED" in line and "127.0.0.1" in line for line in netstat_lines(port))


def check_core(core_url: str, expected_version: str) -> tuple[list[Check], dict[str, Any]]:
    ok, data = http_json(f"{core_url.rstrip('/')}/health")
    if not ok:
        return [Check("core_bridge", False, str(data))], {}
    assert isinstance(data, dict)
    autonomous = data.get("autonomous_maintenance")
    auto_detail = ""
    if isinstance(autonomous, dict):
        auto_detail = (
            f" autonomous={autonomous.get('enabled', 'unknown')}"
            f"/task={autonomous.get('task_running', 'unknown')}"
            f" runs={autonomous.get('run_count', 'unknown')}"
            f" next={autonomous.get('next_run_at', 'unknown')}"
        )
    detail = (
        f"version={data.get('version', 'unknown')} "
        f"sessions={data.get('sessions', 'unknown')} "
        f"closed={data.get('closed', 'unknown')}"
        f"{auto_detail}"
    )
    running_version = str(data.get("version", "unknown"))
    return [
        Check("core_bridge", bool(data.get("ok")), detail),
        Check(
            "core_bridge_version",
            bool(running_version == expected_version),
            f"running={running_version} source={expected_version}",
        ),
    ], data


def check_ports() -> list[Check]:
    checks = [
        Check("xinyu_qq_gateway_6199", tcp_connect("127.0.0.1", 6199), "tcp connect 127.0.0.1:6199"),
        Check("napcat_webui_6099", tcp_connect("127.0.0.1", 6099), "tcp connect 127.0.0.1:6099"),
    ]
    checks.append(
        Check(
            "napcat_to_xinyu_qq_gateway_ws",
            has_established_local(6199),
            "local ESTABLISHED connection on 6199",
        )
    )
    return checks


def check_qq_gateway_config(root: Path, config_path: Path) -> list[Check]:
    cfg = load_json(config_path)
    gateway_path = root / "xinyu_qq_gateway.py"
    version = extract_gateway_version(gateway_path)
    owner_ids = cfg.get("owner_user_ids")
    whitelist_ids = cfg.get("whitelist_user_ids")
    owner_count = len(owner_ids) if isinstance(owner_ids, list) else 0
    whitelist_count = len(whitelist_ids) if isinstance(whitelist_ids, list) else 0
    group_prefixes = cfg.get("group_trigger_prefixes")
    group_prefix_count = len(group_prefixes) if isinstance(group_prefixes, list) else 0
    return [
        Check("qq_gateway_source_present", gateway_path.exists(), f"version={version}"),
        Check("qq_gateway_config_present", bool(cfg), redact_local_path(str(config_path)) if cfg else "missing"),
        Check("qq_gateway_enabled", bool(cfg.get("enabled")), f"value={cfg.get('enabled', 'missing')}"),
        Check("qq_gateway_core_url", str(cfg.get("core_chat_url", "")).endswith("/chat"), str(cfg.get("core_chat_url", ""))),
        Check("qq_gateway_whitelist", owner_count > 0 and whitelist_count > 0, f"owners={owner_count} whitelist={whitelist_count}"),
        Check(
            "qq_gateway_group_trigger",
            group_prefix_count > 0,
            f"mode={cfg.get('group_trigger_mode', 'missing')} prefixes={group_prefix_count}",
        ),
    ]


def status_fields(root: Path) -> dict[str, str]:
    proactive = read_text(root / "memory/context/proactive_presence_state.md")
    dispatch = read_text(root / "memory/context/proactive_qq_dispatch_state.md")
    review = read_text(root / "memory/self/ai_self_iteration_review_state.md")
    gate = read_text(root / "memory/self/ai_self_iteration_state.md")
    capability = read_text(root / "memory/context/capability_zones_state.md")
    return {
        "proactive_evaluated_at": extract_value(proactive, "evaluated_at", "missing"),
        "proactive_decision": extract_value(proactive, "proactive_decision", "missing"),
        "proactive_reason": extract_value(proactive, "reason", "missing"),
        "qq_send_permission": extract_value(proactive, "qq_send_permission", "missing"),
        "candidate_message": extract_value(proactive, "candidate_message", "missing"),
        "last_claim_status": extract_value(dispatch, "last_claim_status", "missing"),
        "last_claim_id": mask_private_identifier(extract_value(dispatch, "last_claim_id", "missing")),
        "last_ack_status": extract_value(dispatch, "last_ack_status", "missing"),
        "adapter_error": extract_value(dispatch, "adapter_error", "missing"),
        "ai_gate_status": extract_value(gate, "gate_status", "missing"),
        "ai_gate_confidence": extract_value(gate, "confidence_score", "missing"),
        "ai_review_permission": extract_value(review, "review_permission", "missing"),
        "ai_review_stable_profile": extract_value(review, "stable_profile_write_permission", "missing"),
        "capability_proactive_qq_send": extract_value(capability, "proactive_qq_send", "missing"),
        "capability_private_scope": extract_value(capability, "private_file_scope", "missing"),
        "capability_codex_operator": extract_value(capability, "codex_as_eye_and_hand", "missing"),
        "capability_codex_workspace": redact_local_path(extract_value(capability, "codex_download_workspace", "missing")),
        "capability_qq_external_private": extract_value(capability, "qq_external_private_bridge", "missing"),
        "capability_qq_group": extract_value(capability, "qq_group_bridge", "missing"),
        "capability_qq_priority_passive_group": extract_value(
            capability,
            "qq_priority_passive_learning_group",
            "missing",
        ),
    }


def check_state(root: Path) -> list[Check]:
    fields = status_fields(root)
    return [
        Check(
            "proactive_gate_readable",
            fields["proactive_decision"] != "missing",
            f"{fields['proactive_decision']} ({fields['proactive_reason']})",
        ),
        Check(
            "dispatch_state",
            fields["last_claim_status"] != "missing",
            f"claim={fields['last_claim_status']} ack={fields['last_ack_status']}",
        ),
        Check(
            "ai_self_iteration_review",
            fields["ai_review_permission"] != "missing",
            f"{fields['ai_review_permission']} stable={fields['ai_review_stable_profile']}",
        ),
        Check(
            "capability_zones",
            fields["capability_proactive_qq_send"] != "missing",
            (
                f"proactive_qq_send={fields['capability_proactive_qq_send']} "
                f"codex={fields['capability_codex_operator']} group={fields['capability_qq_group']} "
                f"passive_group={fields['capability_qq_priority_passive_group']}"
            ),
        ),
    ]


def print_section(title: str) -> None:
    print(f"=== {title} ===")


def print_checks(checks: list[Check]) -> None:
    for check in checks:
        status = "OK" if check.ok else "WARN"
        print(f"{status:4} {check.name}: {check.detail}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only XinYu runtime status summary.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--core-url", default=DEFAULT_CORE_URL)
    parser.add_argument("--qq-config", type=Path, default=DEFAULT_QQ_GATEWAY_CONFIG)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    root = args.root.resolve()
    qq_config = args.qq_config.resolve()

    expected_core_version = bridge_source_version(root / "xinyu_core_bridge.py")
    core_checks, core_data = check_core(args.core_url, expected_core_version)
    port_checks = check_ports()
    qq_gateway_checks = check_qq_gateway_config(root, qq_config)
    state_checks = check_state(root)
    fields = status_fields(root)
    all_checks = core_checks + port_checks + qq_gateway_checks + state_checks

    if args.json:
        print(
            json.dumps(
                {
                    "ok": all(check.ok for check in all_checks if check.name != "dispatch_state"),
                    "checks": [check.__dict__ for check in all_checks],
                    "core": redact_core_data(core_data),
                    "fields": fields,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if all(check.ok for check in all_checks if check.name != "dispatch_state") else 1

    print_section("XinYu Runtime")
    print_checks(core_checks)
    print_checks(port_checks)
    print_section("XinYu QQ Gateway")
    print_checks(qq_gateway_checks)
    print_section("XinYu State")
    print_checks(state_checks)
    print_section("Key Fields")
    for key, value in fields.items():
        print(f"{key}: {value}")

    hard_checks = [check for check in all_checks if check.name != "dispatch_state"]
    return 0 if all(check.ok for check in hard_checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
