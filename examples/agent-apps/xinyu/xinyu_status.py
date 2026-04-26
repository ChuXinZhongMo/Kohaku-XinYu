from __future__ import annotations

import argparse
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


DEFAULT_CORE_URL = "http://127.0.0.1:8765"
DEFAULT_ASTRBOT_ROOT = Path("D:/XinYu/AstrBot")


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


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


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


def check_core(core_url: str) -> tuple[list[Check], dict[str, Any]]:
    ok, data = http_json(f"{core_url.rstrip('/')}/health")
    if not ok:
        return [Check("core_bridge", False, str(data))], {}
    assert isinstance(data, dict)
    detail = (
        f"version={data.get('version', 'unknown')} "
        f"sessions={data.get('sessions', 'unknown')} "
        f"closed={data.get('closed', 'unknown')}"
    )
    return [Check("core_bridge", bool(data.get("ok")), detail)], data


def check_ports() -> list[Check]:
    checks = [
        Check("astrbot_dashboard_6185", tcp_connect("127.0.0.1", 6185), "tcp connect 127.0.0.1:6185"),
        Check("astrbot_onebot_6199", tcp_connect("127.0.0.1", 6199), "tcp connect 127.0.0.1:6199"),
        Check("napcat_webui_6099", tcp_connect("127.0.0.1", 6099), "tcp connect 127.0.0.1:6099"),
    ]
    checks.append(
        Check(
            "napcat_to_astrbot_ws",
            has_established_local(6199),
            "local ESTABLISHED connection on 6199",
        )
    )
    return checks


def check_astrbot_config(astrbot_root: Path) -> list[Check]:
    cfg_path = astrbot_root / "data/config/xinyu_bridge_config.json"
    plugin_path = astrbot_root / "data/plugins/xinyu_bridge/main.py"
    metadata_path = astrbot_root / "data/plugins/xinyu_bridge/metadata.yaml"
    cfg = load_json(cfg_path)
    proactive_enabled = bool(cfg.get("proactive_enabled"))
    target = str(cfg.get("proactive_target_session") or "")
    plugin_text = read_text(plugin_path)
    metadata = read_text(metadata_path)
    return [
        Check("astrbot_plugin_installed", plugin_path.exists(), str(plugin_path)),
        Check(
            "astrbot_plugin_version",
            'SHELL_VERSION = "0.3.0"' in plugin_text or "version: 0.3.0" in metadata,
            "expected xinyu_bridge 0.3.0",
        ),
        Check("astrbot_config_present", bool(cfg), str(cfg_path)),
        Check("proactive_enabled", proactive_enabled, f"value={proactive_enabled}"),
        Check("proactive_target_session", bool(target), target or "missing"),
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
        "last_claim_id": extract_value(dispatch, "last_claim_id", "missing"),
        "last_ack_status": extract_value(dispatch, "last_ack_status", "missing"),
        "adapter_error": extract_value(dispatch, "adapter_error", "missing"),
        "ai_gate_status": extract_value(gate, "gate_status", "missing"),
        "ai_gate_confidence": extract_value(gate, "confidence_score", "missing"),
        "ai_review_permission": extract_value(review, "review_permission", "missing"),
        "ai_review_stable_profile": extract_value(review, "stable_profile_write_permission", "missing"),
        "capability_proactive_qq_send": extract_value(capability, "proactive_qq_send", "missing"),
        "capability_private_scope": extract_value(capability, "private_file_scope", "missing"),
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
            f"proactive_qq_send={fields['capability_proactive_qq_send']}",
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
    parser.add_argument("--astrbot-root", type=Path, default=DEFAULT_ASTRBOT_ROOT)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    root = args.root.resolve()
    astrbot_root = args.astrbot_root.resolve()

    core_checks, core_data = check_core(args.core_url)
    port_checks = check_ports()
    astrbot_checks = check_astrbot_config(astrbot_root)
    state_checks = check_state(root)
    fields = status_fields(root)
    all_checks = core_checks + port_checks + astrbot_checks + state_checks

    if args.json:
        print(
            json.dumps(
                {
                    "ok": all(check.ok for check in all_checks if check.name != "dispatch_state"),
                    "checks": [check.__dict__ for check in all_checks],
                    "core": core_data,
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
    print_section("AstrBot Shell")
    print_checks(astrbot_checks)
    print_section("XinYu State")
    print_checks(state_checks)
    print_section("Key Fields")
    for key, value in fields.items():
        print(f"{key}: {value}")

    hard_checks = [check for check in all_checks if check.name != "dispatch_state"]
    return 0 if all(check.ok for check in hard_checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
