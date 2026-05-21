from __future__ import annotations

from datetime import datetime
from typing import Any

from xinyu_bridge_values import safe_str


def parse_timestamp_iso(value: Any) -> datetime | None:
    text = safe_str(value).strip()
    if not text or text.lower() in {"none", "unknown", "null", "n/a", "na"}:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def timestamp_or_now_iso(value: Any) -> str:
    parsed = parse_timestamp_iso(value)
    if parsed is None:
        return datetime.now().astimezone().isoformat()
    return parsed.astimezone().isoformat()
