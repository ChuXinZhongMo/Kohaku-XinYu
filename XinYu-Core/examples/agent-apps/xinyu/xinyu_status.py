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

from xinyu_runtime_security import (
    bridge_source_version,
    runtime_source_paths,
    source_file_digest,
    source_files_digest,
)
from xinyu_text_variants import legacy_mojibake_variants


DEFAULT_CORE_URL = "http://127.0.0.1:8765"
DEFAULT_QQ_GATEWAY_CONFIG = Path(__file__).resolve().with_name("xinyu_qq_gateway.config.json")
NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

TEXT_HEALTH_FILES = (
    "memory/context/proactive_presence_state.md",
    "memory/context/proactive_request_state.md",
    "memory/context/proactive_qq_dispatch_state.md",
    "memory/context/memory_braid_state.md",
    "memory/context/turn_coherence_state.md",
    "memory/context/initiative_spine_state.md",
    "memory/context/self_state_capsule_state.md",
    "memory/context/self_chosen_goal_ecology_state.md",
    "memory/context/self_action_gateway_state.md",
    "memory/context/self_action_gateway_execution_handoff.md",
    "memory/context/self_action_patch_executor_state.md",
    "memory/context/self_action_patch_executor_task.md",
    "memory/context/self_thought_state.md",
    "memory/context/emotion_council_state.md",
    "memory/context/impulse_soup_state.md",
    "memory/context/early_visible_segment_shadow_state.md",
    "memory/self/learning_closed_loop_state.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
)

TEXT_HEALTH_MARKERS = (
    "\u54e5",
    "\u4e3b\u4eba",
    "\u8bb0\u5fc6",
    "\u53cd\u601d\u961f\u5217",
    "\u5173\u4e8e\u88ab\u8bb0\u4f4f",
    "\u8fd8\u6ca1\u653e\u4e0b",
    "\u957f\u671f\u5173\u7cfb",
    "\u5177\u4f53\u5bf9\u8bdd",
    "\u8bb0\u5fc6\u7559\u75d5",
    "\u5916\u90e8\u5b66\u4e60",
    "\u4e3b\u52a8\u7ebf\u7a0b",
    "\u60c5\u611f\u7cfb\u7edf",
    "\u4e3b\u4eba\u683c",
)


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def runtime_text_health_issues(root: Path) -> list[str]:
    issues: list[str] = []
    for rel_path in TEXT_HEALTH_FILES:
        path = root / rel_path
        if not path.exists():
            continue
        text = read_text(path)
        if "\ufffd" in text:
            issues.append(f"{rel_path}:replacement_character")
        marker_hits: list[str] = []
        for marker in TEXT_HEALTH_MARKERS:
            if any(variant in text for variant in legacy_mojibake_variants(marker)):
                marker_hits.append(marker)
        if marker_hits:
            issues.append(f"{rel_path}:legacy_mojibake:{len(marker_hits)}")
    return issues


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
    if "examples" in lowered and "agent-apps" in lowered and "xinyu" in lowered:
        return "<xinyu_dir>"
    if re.search(r"(?i)([a-z]:\\|/users/|/home/|\\\\)", text):
        return "<local_path>"
    return text


def redact_core_data(data: dict[str, Any]) -> dict[str, Any]:
    return _redact_status_value(data)


def _redact_status_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_local_path(value)
    if isinstance(value, dict):
        return {key: _redact_status_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_status_value(item) for item in value]
    return value


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
        with NO_PROXY_OPENER.open(url, timeout=timeout) as response:
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


def check_core(
    core_url: str,
    expected_version: str,
    expected_source_digest: str,
    expected_runtime_source_digest: str,
) -> tuple[list[Check], dict[str, Any]]:
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
    running_source_digest = str(data.get("source_digest", "unknown"))
    running_runtime_source_digest = str(data.get("runtime_source_digest", "unknown"))
    return [
        Check("core_bridge", bool(data.get("ok")), detail),
        Check(
            "core_bridge_version",
            bool(running_version == expected_version),
            f"running={running_version} source={expected_version}",
        ),
        Check(
            "core_bridge_source_digest",
            bool(running_source_digest == expected_source_digest),
            f"running={running_source_digest} source={expected_source_digest}",
        ),
        Check(
            "core_bridge_runtime_source_digest",
            bool(running_runtime_source_digest == expected_runtime_source_digest),
            f"running={running_runtime_source_digest} source={expected_runtime_source_digest}",
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
    codex_prefixes = cfg.get("codex_command_prefixes")
    codex_prefix_list = codex_prefixes if isinstance(codex_prefixes, list) else []
    codex_execute_url = str(cfg.get("codex_execute_url", ""))
    outbox_claim_url = str(cfg.get("qq_outbox_claim_url", ""))
    outbox_ack_url = str(cfg.get("qq_outbox_ack_url", ""))
    return [
        Check("qq_gateway_source_present", gateway_path.exists(), f"version={version}"),
        Check("qq_gateway_config_present", bool(cfg), redact_local_path(str(config_path)) if cfg else "missing"),
        Check("qq_gateway_enabled", bool(cfg.get("enabled")), f"value={cfg.get('enabled', 'missing')}"),
        Check("qq_gateway_core_url", str(cfg.get("core_chat_url", "")).endswith("/chat"), str(cfg.get("core_chat_url", ""))),
        Check(
            "qq_gateway_codex_route",
            bool(cfg.get("codex_command_enabled"))
            and codex_execute_url.endswith("/codex/execute")
            and "/codex" in codex_prefix_list,
            (
                f"enabled={cfg.get('codex_command_enabled', 'missing')} "
                f"url={codex_execute_url or 'missing'} prefixes={len(codex_prefix_list)}"
            ),
        ),
        Check(
            "qq_gateway_outbox_route",
            bool(cfg.get("qq_outbox_enabled"))
            and outbox_claim_url.endswith("/qq/outbox/claim")
            and outbox_ack_url.endswith("/qq/outbox/ack"),
            (
                f"enabled={cfg.get('qq_outbox_enabled', 'missing')} "
                f"claim={outbox_claim_url or 'missing'} ack={outbox_ack_url or 'missing'}"
            ),
        ),
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
    outbox = read_text(root / "memory/context/qq_outbox_dispatch_state.md")
    review = read_text(root / "memory/self/ai_self_iteration_review_state.md")
    gate = read_text(root / "memory/self/ai_self_iteration_state.md")
    capability = read_text(root / "memory/context/capability_zones_state.md")
    v1_canary = read_text(root / "memory/context/v1_canary_readiness_state.md")
    initiative_spine = read_text(root / "memory/context/initiative_spine_state.md")
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
        "qq_outbox_queued": extract_value(outbox, "queued_count", "missing"),
        "qq_outbox_claimed": extract_value(outbox, "claimed_count", "missing"),
        "qq_outbox_sent": extract_value(outbox, "sent_count", "missing"),
        "qq_outbox_failed": extract_value(outbox, "failed_count", "missing"),
        "v1_canary_decision": extract_value(v1_canary, "readiness_decision", "missing"),
        "v1_canary_switch_permission": extract_value(v1_canary, "switch_permission", "missing"),
        "v1_canary_auto_full_switch": extract_value(v1_canary, "auto_full_switch", "missing"),
        "v1_canary_proposal_status": extract_value(v1_canary, "proposal_status", "missing"),
        "v1_canary_sample_window": extract_value(v1_canary, "sample_window_turns", "missing"),
        "v1_canary_error_rate": extract_value(v1_canary, "error_rate", "missing"),
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
        "initiative_spine_status": extract_value(initiative_spine, "status", "missing"),
        "initiative_spine_emergence": extract_value(initiative_spine, "emergence_level", "missing"),
        "initiative_spine_action": extract_value(initiative_spine, "action_permission", "missing"),
        "initiative_spine_next_step": extract_value(initiative_spine, "next_step", "missing"),
    }


def check_state(root: Path) -> list[Check]:
    fields = status_fields(root)
    text_health_issues = runtime_text_health_issues(root)
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
            "qq_outbox_dispatch_state",
            True,
            (
                f"queued={fields['qq_outbox_queued']} claimed={fields['qq_outbox_claimed']} "
                f"sent={fields['qq_outbox_sent']} failed={fields['qq_outbox_failed']}"
            ),
        ),
        Check(
            "v1_canary_readiness",
            True,
            (
                f"{fields['v1_canary_decision']} proposal={fields['v1_canary_proposal_status']} "
                f"sample={fields['v1_canary_sample_window']} error_rate={fields['v1_canary_error_rate']} "
                f"auto_full_switch={fields['v1_canary_auto_full_switch']}"
            ),
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
        Check(
            "initiative_spine_state",
            True,
            (
                f"{fields['initiative_spine_status']} "
                f"emergence={fields['initiative_spine_emergence']} "
                f"action={fields['initiative_spine_action']}"
            ),
        ),
        Check(
            "runtime_text_utf8_health",
            not text_health_issues,
            "ok" if not text_health_issues else "; ".join(text_health_issues[:5]),
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
    expected_core_digest = source_file_digest(root / "xinyu_core_bridge.py")
    expected_runtime_digest = source_files_digest(runtime_source_paths(root))
    core_checks, core_data = check_core(
        args.core_url,
        expected_core_version,
        expected_core_digest,
        expected_runtime_digest,
    )
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
