from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from xinyu_runtime_security import bridge_source_version


HARD_CHECKS = {
    "core_bridge",
    "core_bridge_version",
    "xinyu_qq_gateway_6199",
    "napcat_webui_6099",
    "napcat_to_xinyu_qq_gateway_ws",
    "qq_gateway_source_present",
    "qq_gateway_config_present",
    "qq_gateway_enabled",
    "qq_gateway_core_url",
    "qq_gateway_whitelist",
    "qq_gateway_group_trigger",
    "proactive_gate_readable",
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
    if completed.returncode != 0:
        raise RuntimeError(
            "xinyu_status.py --json failed with exit code "
            f"{completed.returncode}: {completed.stdout[-500:]} {completed.stderr[-500:]}"
        )
    return json.loads(completed.stdout)


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
