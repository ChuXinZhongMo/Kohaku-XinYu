from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from schemas import VALID_DRIVES, VALID_EMOTION_LENSES, VALID_MODES


KIND = "xinyu_maia_behavior_case"
VALID_SOURCES = {"cped_reviewed_delegated", "cped_raw_assistant_suggested"}
VALID_REVIEW_LEVELS = {
    "reviewed_delegated_behavior_seed",
    "assistant_suggested_needs_owner_review",
}
VALID_ORIGINS = {"reviewed_seed_v001", "raw_cped_rule_suggested_v001"}
VALID_BIAS_SOURCES = {
    "assistant_draft_needs_owner_review",
    "review_label_default_needs_owner_review",
    "assistant_suggested_rule_needs_owner_review",
}
VALID_TOOL_BOUNDARIES = {"none", "no_tool"}
TARGET_MODE_COUNTS = {"reply": 350, "clarify": 100, "wait": 50}

REQUIRED_TOP_KEYS = {
    "anti_patterns",
    "candidate_origin",
    "context",
    "draft_review",
    "expected",
    "id",
    "kind",
    "language",
    "review_level",
    "source",
    "source_id",
    "source_license",
    "tags",
    "user_text",
}
REQUIRED_EXPECTED_KEYS = {
    "desired_texture",
    "dominant_drives",
    "emotion_lenses",
    "memory_candidate",
    "mode",
    "reply_bias",
    "reply_bias_source",
    "tool_boundary",
}
REQUIRED_DRAFT_KEYS = {
    "assistant_draft_visible_reply_example",
    "convert_to_training_candidate",
    "source_public_reply_used",
    "status",
    "target_reply_bias",
    "training_allowed",
    "visible_reply_example_is_training_target",
}
SECRET_PATTERNS = {
    "raw_windows_path": re.compile(r"[A-Za-z]:\\"),
    "openai_key": re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    "secret_assignment": re.compile(r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}"),
    "private_file": re.compile(r"(?i)(\.env|\.xinyu_bridge_token)"),
}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def validate_row(row: dict[str, Any], line_no: int, failures: list[str]) -> tuple[str, str, str] | None:
    missing = REQUIRED_TOP_KEYS - set(row)
    extra = set(row) - REQUIRED_TOP_KEYS
    if missing:
        failures.append(f"line {line_no}: missing top-level keys {sorted(missing)!r}")
        return None
    if extra:
        failures.append(f"line {line_no}: unexpected top-level keys {sorted(extra)!r}")
    if row.get("kind") != KIND:
        failures.append(f"line {line_no}: invalid kind {row.get('kind')!r}")
    if row.get("source") not in VALID_SOURCES:
        failures.append(f"line {line_no}: invalid source {row.get('source')!r}")
    if row.get("candidate_origin") not in VALID_ORIGINS:
        failures.append(f"line {line_no}: invalid candidate_origin {row.get('candidate_origin')!r}")
    if row.get("review_level") not in VALID_REVIEW_LEVELS:
        failures.append(f"line {line_no}: invalid review_level {row.get('review_level')!r}")
    if row.get("language") != "zh":
        failures.append(f"line {line_no}: language must be zh")
    if not str(row.get("id") or "").startswith("xinyu-maia-zh-behavior-candidate-v001-"):
        failures.append(f"line {line_no}: bad candidate id prefix")
    if not str(row.get("user_text") or "").strip():
        failures.append(f"line {line_no}: empty user_text")
    if not isinstance(row.get("context"), dict):
        failures.append(f"line {line_no}: context must be object")

    expected = row.get("expected")
    if not isinstance(expected, dict):
        failures.append(f"line {line_no}: expected must be object")
        return None
    missing_expected = REQUIRED_EXPECTED_KEYS - set(expected)
    extra_expected = set(expected) - REQUIRED_EXPECTED_KEYS
    if missing_expected:
        failures.append(f"line {line_no}: missing expected keys {sorted(missing_expected)!r}")
        return None
    if extra_expected:
        failures.append(f"line {line_no}: unexpected expected keys {sorted(extra_expected)!r}")

    mode = str(expected.get("mode") or "")
    if mode not in VALID_MODES:
        failures.append(f"line {line_no}: invalid mode {mode!r}")
    if mode not in {"reply", "clarify", "wait"}:
        failures.append(f"line {line_no}: candidate pool should not use external mode {mode!r}")
    lenses = [str(item) for item in as_list(expected.get("emotion_lenses"))]
    drives = [str(item) for item in as_list(expected.get("dominant_drives"))]
    if not lenses or any(item not in VALID_EMOTION_LENSES for item in lenses):
        failures.append(f"line {line_no}: invalid emotion_lenses {lenses!r}")
    if not drives or any(item not in VALID_DRIVES for item in drives):
        failures.append(f"line {line_no}: invalid dominant_drives {drives!r}")
    if not str(expected.get("reply_bias") or "").strip():
        failures.append(f"line {line_no}: empty reply_bias")
    bias_source = str(expected.get("reply_bias_source") or "")
    if bias_source not in VALID_BIAS_SOURCES:
        failures.append(f"line {line_no}: invalid reply_bias_source {bias_source!r}")
    if bool(expected.get("memory_candidate")):
        failures.append(f"line {line_no}: public zh behavior candidate cannot be memory_candidate")
    boundary = str(expected.get("tool_boundary") or "")
    if boundary not in VALID_TOOL_BOUNDARIES:
        failures.append(f"line {line_no}: invalid tool_boundary {boundary!r}")
    if mode == "wait" and boundary != "none":
        failures.append(f"line {line_no}: wait must use boundary none")
    if mode != "wait" and boundary != "no_tool":
        failures.append(f"line {line_no}: non-wait rows must use no_tool")

    draft = row.get("draft_review")
    if not isinstance(draft, dict):
        failures.append(f"line {line_no}: draft_review must be object")
        return None
    missing_draft = REQUIRED_DRAFT_KEYS - set(draft)
    extra_draft = set(draft) - REQUIRED_DRAFT_KEYS
    if missing_draft:
        failures.append(f"line {line_no}: missing draft_review keys {sorted(missing_draft)!r}")
    if extra_draft:
        failures.append(f"line {line_no}: unexpected draft_review keys {sorted(extra_draft)!r}")
    if draft.get("status") != "needs_owner_review_before_training":
        failures.append(f"line {line_no}: draft status must be needs_owner_review_before_training")
    if str(draft.get("target_reply_bias") or "").strip():
        failures.append(f"line {line_no}: formal target_reply_bias must remain empty")
    for key in (
        "convert_to_training_candidate",
        "training_allowed",
        "source_public_reply_used",
        "visible_reply_example_is_training_target",
    ):
        if draft.get(key) is True:
            failures.append(f"line {line_no}: {key} must not be true")

    anti_patterns = [str(item) for item in as_list(row.get("anti_patterns"))]
    tags = [str(item) for item in as_list(row.get("tags"))]
    if len(anti_patterns) < 3:
        failures.append(f"line {line_no}: expected at least three anti_patterns")
    for tag in ("xinyu_maia_zh_behavior_v001", "candidate_pool_v001", "review_only", "not_training", mode):
        if tag not in tags:
            failures.append(f"line {line_no}: missing tag {tag!r}")

    blob = json.dumps(row, ensure_ascii=False, sort_keys=True)
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(blob):
            failures.append(f"line {line_no}: unsafe text matched {name}")
    return mode, bias_source, boundary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default=str(ROOT / "data" / "review" / "xinyu_maia_zh_behavior_candidate_pool_v001.jsonl"),
    )
    args = parser.parse_args()
    path = Path(args.path)

    failures: list[str] = []
    modes: Counter[str] = Counter()
    bias_sources: Counter[str] = Counter()
    boundaries: Counter[str] = Counter()
    origins: Counter[str] = Counter()
    count = 0

    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            count += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                failures.append(f"line {line_no}: invalid JSON: {exc}")
                continue
            if not isinstance(row, dict):
                failures.append(f"line {line_no}: row is not object")
                continue
            origins[str(row.get("candidate_origin") or "")] += 1
            result = validate_row(row, line_no, failures)
            if result is None:
                continue
            mode, bias_source, boundary = result
            modes[mode] += 1
            bias_sources[bias_source] += 1
            boundaries[boundary] += 1

    if count != 500:
        failures.append(f"expected row_count=500, got {count}")
    if modes != Counter(TARGET_MODE_COUNTS):
        failures.append(f"unexpected mode distribution {dict(modes)!r}")
    if origins.get("reviewed_seed_v001", 0) != 27:
        failures.append(f"expected reviewed_seed_v001=27, got {origins.get('reviewed_seed_v001', 0)}")

    print(f"rows={count}")
    print("modes=" + json.dumps(dict(sorted(modes.items())), ensure_ascii=False, sort_keys=True))
    print("origins=" + json.dumps(dict(sorted(origins.items())), ensure_ascii=False, sort_keys=True))
    print("bias_sources=" + json.dumps(dict(sorted(bias_sources.items())), ensure_ascii=False, sort_keys=True))
    print("boundaries=" + json.dumps(dict(sorted(boundaries.items())), ensure_ascii=False, sort_keys=True))
    if failures:
        for failure in failures[:60]:
            print("FAIL " + failure)
        print(f"failure_count={len(failures)}")
        return 1
    print("validation_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
