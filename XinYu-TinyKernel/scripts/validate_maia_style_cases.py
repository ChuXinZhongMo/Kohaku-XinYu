from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from schemas import VALID_DRIVES, VALID_EMOTION_LENSES, VALID_MODES


KIND = "maia_style_behavior_case"
VALID_TOOL_BOUNDARIES = {
    "none",
    "no_tool",
    "approval_required",
    "read_only_probe",
    "shadow_only",
    "local_only",
}
VALID_SOURCES = {"handwritten_sanitized", "abstracted_sanitized"}
REQUIRED_TOP_KEYS = {
    "id",
    "kind",
    "source",
    "user_text",
    "context",
    "expected",
    "anti_patterns",
    "tags",
}
REQUIRED_EXPECTED_KEYS = {
    "mode",
    "emotion_lenses",
    "dominant_drives",
    "reply_bias",
    "memory_candidate",
    "tool_boundary",
}
SECRET_PATTERNS = {
    "raw_windows_path": re.compile(r"[A-Za-z]:\\"),
    "openai_key": re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    "secret_assignment": re.compile(r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}"),
    "private_file": re.compile(r"(?i)(\.env|\.xinyu_bridge_token)"),
}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text_blob(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, sort_keys=True)


def _check_text_safety(row: dict[str, Any], line_no: int, failures: list[str]) -> None:
    blob = _text_blob(row)
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(blob):
            failures.append(f"line {line_no}: unsafe text matched {name}")


def _validate_row(row: dict[str, Any], line_no: int, failures: list[str]) -> tuple[str, str] | None:
    extra = set(row) - REQUIRED_TOP_KEYS
    missing = REQUIRED_TOP_KEYS - set(row)
    if extra:
        failures.append(f"line {line_no}: unexpected top-level keys {sorted(extra)!r}")
    if missing:
        failures.append(f"line {line_no}: missing top-level keys {sorted(missing)!r}")
        return None
    if row.get("kind") != KIND:
        failures.append(f"line {line_no}: invalid kind {row.get('kind')!r}")
    if row.get("source") not in VALID_SOURCES:
        failures.append(f"line {line_no}: invalid source {row.get('source')!r}")
    if not str(row.get("id") or "").startswith("maia-style-v001-"):
        failures.append(f"line {line_no}: id must start with maia-style-v001-")
    if not str(row.get("user_text") or "").strip():
        failures.append(f"line {line_no}: user_text is empty")
    if not isinstance(row.get("context"), dict):
        failures.append(f"line {line_no}: context must be object")

    expected = row.get("expected")
    if not isinstance(expected, dict):
        failures.append(f"line {line_no}: expected must be object")
        return None
    expected_extra = set(expected) - REQUIRED_EXPECTED_KEYS
    expected_missing = REQUIRED_EXPECTED_KEYS - set(expected)
    if expected_extra:
        failures.append(f"line {line_no}: unexpected expected keys {sorted(expected_extra)!r}")
    if expected_missing:
        failures.append(f"line {line_no}: missing expected keys {sorted(expected_missing)!r}")
        return None

    mode = str(expected.get("mode") or "")
    if mode not in VALID_MODES:
        failures.append(f"line {line_no}: invalid mode {mode!r}")
    lenses = [str(item) for item in _as_list(expected.get("emotion_lenses"))]
    drives = [str(item) for item in _as_list(expected.get("dominant_drives"))]
    if not lenses or any(item not in VALID_EMOTION_LENSES for item in lenses):
        failures.append(f"line {line_no}: invalid emotion_lenses {lenses!r}")
    if not drives or any(item not in VALID_DRIVES for item in drives):
        failures.append(f"line {line_no}: invalid dominant_drives {drives!r}")
    if not str(expected.get("reply_bias") or "").strip():
        failures.append(f"line {line_no}: reply_bias is empty")
    if not isinstance(expected.get("memory_candidate"), bool):
        failures.append(f"line {line_no}: memory_candidate must be boolean")
    boundary = str(expected.get("tool_boundary") or "")
    if boundary not in VALID_TOOL_BOUNDARIES:
        failures.append(f"line {line_no}: invalid tool_boundary {boundary!r}")

    anti_patterns = [str(item) for item in _as_list(row.get("anti_patterns"))]
    tags = [str(item) for item in _as_list(row.get("tags"))]
    if len(anti_patterns) < 2:
        failures.append(f"line {line_no}: expected at least two anti_patterns")
    if mode and mode not in tags:
        failures.append(f"line {line_no}: tags must include expected mode {mode!r}")
    if "maia_style" not in tags and mode not in {"wait", "clarify", "status_probe", "codex_delegate", "local_only_limitation"}:
        failures.append(f"line {line_no}: non-routing cases should include maia_style tag")

    if mode in {"codex_delegate", "status_probe", "memory_candidate"} and boundary not in {
        "approval_required",
        "read_only_probe",
    }:
        failures.append(f"line {line_no}: external mode {mode!r} has weak boundary {boundary!r}")
    if mode == "status_probe" and boundary != "read_only_probe":
        failures.append(f"line {line_no}: status_probe must use read_only_probe boundary")
    if mode == "local_only_limitation" and boundary != "local_only":
        failures.append(f"line {line_no}: local_only_limitation must use local_only boundary")
    if mode == "wait" and expected.get("memory_candidate"):
        failures.append(f"line {line_no}: wait case cannot be a memory candidate")

    _check_text_safety(row, line_no, failures)
    return (mode, boundary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(ROOT / "eval" / "maia_style_behavior_cases_v001.jsonl"))
    args = parser.parse_args()
    path = Path(args.path)
    failures: list[str] = []
    count = 0
    modes: dict[str, int] = {}
    boundaries: dict[str, int] = {}

    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            count += 1
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                failures.append(f"line {line_no}: invalid JSON: {exc}")
                continue
            if not isinstance(value, dict):
                failures.append(f"line {line_no}: row is not an object")
                continue
            result = _validate_row(value, line_no, failures)
            if result is None:
                continue
            mode, boundary = result
            modes[mode] = modes.get(mode, 0) + 1
            boundaries[boundary] = boundaries.get(boundary, 0) + 1

    missing_modes = sorted(VALID_MODES - set(modes))
    if missing_modes:
        failures.append(f"missing expected mode coverage: {missing_modes!r}")

    print(f"rows={count}")
    print("modes=" + json.dumps(modes, ensure_ascii=False, sort_keys=True))
    print("boundaries=" + json.dumps(boundaries, ensure_ascii=False, sort_keys=True))
    if failures:
        for failure in failures[:50]:
            print("FAIL " + failure)
        print(f"failure_count={len(failures)}")
        return 1
    print("validation_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
