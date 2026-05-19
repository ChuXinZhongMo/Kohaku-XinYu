from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlparse

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


def read_text_safe(path: Path) -> str:
    try:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


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


desktop_replace_frontmatter_field = replace_frontmatter_field
desktop_replace_list_field = replace_list_field


def _replacement_value(field: str, value: str) -> str:
    text = safe_str(value).strip()
    if text:
        return text
    if field in TIMESTAMP_FIELD_NAMES:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    return "none"


def parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def seconds_since_iso(value: str, *, default: float = 999999.0) -> float:
    parsed = parse_iso(value)
    if parsed is None:
        return default
    return max(0.0, (datetime.now().astimezone() - parsed).total_seconds())


def iso_from_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value).astimezone().isoformat()


def payload_event_time_iso(payload: Mapping[str, Any] | None, *, fallback: str = "") -> str:
    parsed = _payload_event_datetime(payload)
    if parsed is not None:
        return parsed.astimezone().isoformat()
    return safe_str(fallback).strip()


def payload_event_timestamp_seconds(payload: Mapping[str, Any] | None, *, fallback: int | None = None) -> int:
    parsed = _payload_event_datetime(payload)
    if parsed is not None:
        return int(parsed.timestamp())
    if fallback is not None:
        return int(fallback)
    return int(datetime.now().astimezone().timestamp())


def payload_path(value: str) -> Path:
    text = value.strip()
    if text.lower().startswith("file://"):
        parsed = urlparse(text)
        path_text = parsed.path
        if os.name == "nt" and len(path_text) > 2 and path_text[0] == "/" and path_text[2] == ":":
            path_text = path_text[1:]
        return Path(unquote(path_text))
    return Path(text)


def _payload_event_datetime(payload: Mapping[str, Any] | None) -> datetime | None:
    if not isinstance(payload, Mapping):
        return None
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    for value in (
        payload.get("event_time"),
        payload.get("recorded_at"),
        payload.get("created_at"),
        payload.get("timestamp"),
        payload.get("time"),
        metadata.get("event_time"),
        metadata.get("recorded_at"),
        metadata.get("created_at"),
        metadata.get("timestamp"),
        metadata.get("time"),
        metadata.get("qq_event_time_iso"),
        metadata.get("desktop_event_time_iso"),
    ):
        parsed = _coerce_event_datetime(value)
        if parsed is not None:
            return parsed
    return None


def _coerce_event_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.astimezone()
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return _datetime_from_timestamp(float(value))
    text = safe_str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        try:
            return _datetime_from_timestamp(float(text))
        except ValueError:
            return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.astimezone()


def _datetime_from_timestamp(value: float) -> datetime | None:
    if value <= 0:
        return None
    if value > 10_000_000_000:
        value = value / 1000.0
    try:
        return datetime.fromtimestamp(value).astimezone()
    except (OSError, OverflowError, ValueError):
        return None
