from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from xinyu_runtime_security import bridge_source_version, source_file_digest, source_files_digest


HARD_CHECKS = {
    "core_bridge",
    "core_bridge_runtime_source_digest",
    "core_bridge_source_digest",
    "core_bridge_version",
    "xinyu_qq_gateway_6199",
    "napcat_webui_6099",
    "napcat_to_xinyu_qq_gateway_ws",
    "qq_gateway_source_present",
    "qq_gateway_config_present",
    "qq_gateway_codex_route",
    "qq_gateway_enabled",
    "qq_gateway_core_url",
    "qq_gateway_outbox_route",
    "qq_gateway_whitelist",
    "qq_gateway_group_trigger",
    "proactive_gate_readable",
    "runtime_text_utf8_health",
}


RAW_PATH_PATTERN = re.compile(r"(?i)([a-z]:\\|/users/|/home/|\\\\)")
RAW_PRIVATE_ID_PATTERN = re.compile(r"\d{5,}")


def _run_status(root: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [str(root / ".venv" / "Scripts" / "python.exe"), "xinyu_status.py", "--json"],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        output = (completed.stdout + "\n" + completed.stderr).strip().splitlines()
        tail = "\n".join(output[-12:])
        raise RuntimeError(
            "xinyu_status.py --json failed with exit code "
            f"{completed.returncode}: {tail}"
        )


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(_walk_strings(item))
        return strings
    if isinstance(value, list):
        strings = []
        for item in value:
            strings.extend(_walk_strings(item))
        return strings
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail on live XinYu deployment/status drift.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    failures: list[str] = []
    status = _run_status(root)
    checks = {item.get("name"): item for item in status.get("checks", []) if isinstance(item, dict)}

    if status.get("ok") is not True:
        failures.append("xinyu_status ok=false")

    for name in sorted(HARD_CHECKS):
        item = checks.get(name)
        if not item:
            failures.append(f"missing check: {name}")
        elif item.get("ok") is not True:
            failures.append(f"{name} failed: {item.get('detail', '')}")

    expected_version = bridge_source_version(root / "xinyu_core_bridge.py")
    running_version = str(status.get("core", {}).get("version", "unknown"))
    if running_version != expected_version:
        failures.append(f"core version mismatch: running={running_version} source={expected_version}")
    expected_source_digest = source_file_digest(root / "xinyu_core_bridge.py")
    running_source_digest = str(status.get("core", {}).get("source_digest", "unknown"))
    if running_source_digest != expected_source_digest:
        failures.append(
            "core source digest mismatch: "
            f"running={running_source_digest} source={expected_source_digest}"
        )
    expected_runtime_source_digest = source_files_digest(
        (
            root / "xinyu_core_bridge.py",
            root / "xinyu_bridge_turn_pipeline.py",
            root / "xinyu_bridge_action_routes.py",
            root / "xinyu_runtime_context.py",
            root / "xinyu_memory_braid.py",
            root / "xinyu_turn_coherence.py",
            root / "xinyu_initiative_spine.py",
            root / "xinyu_emotion_council.py",
            root / "xinyu_speech_controller.py",
        )
    )
    running_runtime_source_digest = str(status.get("core", {}).get("runtime_source_digest", "unknown"))
    if running_runtime_source_digest != expected_runtime_source_digest:
        failures.append(
            "core runtime source digest mismatch: "
            f"running={running_runtime_source_digest} source={expected_runtime_source_digest}"
        )

    raw_path_hits = [
        text
        for text in _walk_strings(status)
        if RAW_PATH_PATTERN.search(text) and not text.startswith("<")
    ]
    if raw_path_hits:
        failures.append(f"status output contains unredacted local paths: {len(raw_path_hits)} string(s)")

    result = {"ok": not failures, "failures": failures}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("deployment_status_smoke:", "ok" if not failures else "failed")
        for failure in failures:
            print(f"- {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
