from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from common import DATA_DIR, compact_space, read_jsonl, write_jsonl


PATH_REPLACEMENTS = (
    (re.compile(r"[A-Za-z]:\\XinYu(?:\\XinYu-TinyKernel|-TinyKernel)(?:\\[^\s\"'锛屻€傦紱;]*)?", re.I), "<tinykernel_root>"),
    (re.compile(r"[A-Za-z]:\\XinYu(?:\\[^\s\"'锛屻€傦紱;]*)?", re.I), "<xinyu_root>"),
    (re.compile(r"[A-Za-z]:\\Users\\[^\s\"'锛屻€傦紱;]+", re.I), "<user_path>"),
)
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
)
LONG_ID_PATTERN = re.compile(r"\b\d{8,}\b")
HASH_PATTERN = re.compile(r"\b[a-f0-9]{24,64}\b", re.I)
STATE_FILE_PATTERN = re.compile(r"\b(memory|runtime|logs)\\[^\s\"'锛屻€傦紱;]+", re.I)


def sanitize_text(text: str) -> str:
    value = str(text or "")
    for pattern, replacement in PATH_REPLACEMENTS:
        value = pattern.sub(replacement, value)
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("<secret>", value)
    value = LONG_ID_PATTERN.sub("<numeric_id>", value)
    value = HASH_PATTERN.sub("<hash>", value)
    value = STATE_FILE_PATTERN.sub("<state_file>", value)
    return compact_space(value)


def sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize_value(item) for key, item in value.items()}
    return value


def has_reject_marker(row: dict[str, Any]) -> tuple[bool, str]:
    text = str(row)
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        return True, "secret_pattern"
    if "xinyu.local.env" in text or ".xinyu_bridge_token" in text:
        return True, "explicit_secret_file"
    target = row.get("target") if isinstance(row.get("target"), dict) else {}
    reply = str(target.get("reply", ""))
    if "<tool_call>" in reply or "<function=" in reply or "memory_read" in reply:
        return True, "pseudo_tool_leak"
    if len(reply) > 900:
        return True, "reply_too_long"
    return False, ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DATA_DIR / "candidates" / "candidates_v0.jsonl"))
    parser.add_argument("--output", default=str(DATA_DIR / "cleaned" / "cleaned_v0.jsonl"))
    parser.add_argument("--rejected", default=str(DATA_DIR / "rejected" / "rejected_v0.jsonl"))
    args = parser.parse_args()

    cleaned: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in read_jsonl(Path(args.input)):
        sanitized = sanitize_value(row)
        reject, reason = has_reject_marker(sanitized)
        if reject:
            if isinstance(sanitized, dict):
                sanitized.setdefault("metadata", {})["reject_reason"] = reason
            rejected.append(sanitized)
        else:
            cleaned.append(sanitized)
    clean_count = write_jsonl(Path(args.output), cleaned)
    reject_count = write_jsonl(Path(args.rejected), rejected)
    print(f"wrote {clean_count} cleaned rows to {args.output}")
    print(f"wrote {reject_count} rejected rows to {args.rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
