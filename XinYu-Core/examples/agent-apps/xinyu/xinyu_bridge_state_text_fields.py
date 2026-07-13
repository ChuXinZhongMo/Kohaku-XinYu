from __future__ import annotations

import re
from datetime import datetime

from xinyu_bridge_stores import read_text_safe
from xinyu_bridge_values import safe_str


TIMESTAMP_FIELD_NAMES = {
    "event_time",
    "observed_at",
    "recorded_at",
    "created_at",
    "updated_at",
    "timestamp",
    "started_at",
    "last_seen_at",
}


def state_field(text: str, field: str, default: str = "") -> str:
    match = re.search(rf"(?m)^-\s+{re.escape(field)}:\s*(.*)$", text or "")
    if not match:
        return default
    return re.sub(r"\s+", " ", match.group(1).strip()) or default


def replace_frontmatter_field(text: str, field: str, value: str) -> str:
    replacement = f"{field}: {_replacement_value(field, value)}"
    updated, count = re.subn(
        rf"(?m)^{re.escape(field)}:\s*.*$",
        replacement,
        text,
        count=1,
    )
    if count:
        return updated
    return text.rstrip() + "\n" + replacement + "\n"


def replace_list_field(text: str, field: str, value: str) -> str:
    replacement = f"- {field}: {_replacement_value(field, value)}"
    updated, count = re.subn(
        rf"(?m)^-\s+{re.escape(field)}:\s*.*$",
        replacement,
        text,
        count=1,
    )
    if count:
        return updated
    return text.rstrip() + "\n" + replacement + "\n"


def _replacement_value(field: str, value: str) -> str:
    text = safe_str(value).strip()
    if text:
        return text
    if field in TIMESTAMP_FIELD_NAMES:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    return "none"
