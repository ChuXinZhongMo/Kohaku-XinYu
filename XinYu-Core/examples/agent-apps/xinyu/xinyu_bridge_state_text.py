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


def build_payload_time_context_block(
    payload: Mapping[str, Any] | None,
    *,
    observed_at: Any = None,
    heading: str = "Live Time Context",
) -> str:
    """Render exact real-world time anchors for the current message.

    ``message_event_time`` is when the adapter says the user message happened.
    ``current_runtime_time`` is when XinYu is building the reply. Both are kept
    because delayed turns must not be interpreted as happening "now".
    """
    observed = _coerce_event_datetime(observed_at) or datetime.now().astimezone()
    if observed.tzinfo is None:
        observed = observed.astimezone()
    event_with_source = _payload_event_datetime_with_source(payload)
    event_source = "runtime_fallback"
    if event_with_source is None:
        event = observed
    else:
        event, event_source = event_with_source
    if event.tzinfo is None:
        event = event.astimezone()
    observed_local = observed.astimezone()
    event_local = event.astimezone()
    age_seconds = int((observed_local - event_local).total_seconds())
    clock_skew = age_seconds < -5
    return "\n".join(
        [
            f"## {safe_str(heading).strip() or 'Live Time Context'}",
            f"current_runtime_time: {observed_local.isoformat(timespec='seconds')}",
            f"current_runtime_unix: {int(observed_local.timestamp())}",
            f"message_event_time: {event_local.isoformat(timespec='seconds')}",
            f"message_event_unix: {int(event_local.timestamp())}",
            f"message_age_seconds: {age_seconds}",
            f"event_time_source: {event_source}",
            f"clock_skew_possible: {str(clock_skew).lower()}",
            (
                "time_policy: use message_event_time for when the owner actually said the message; "
                "use current_runtime_time for the reply moment; use message_age_seconds when judging "
                "waiting, sleep/wake state, emotional residue, and whether older context is stale."
            ),
        ]
    )


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
    event = _payload_event_datetime_with_source(payload)
    return event[0] if event is not None else None


def _payload_event_datetime_with_source(payload: Mapping[str, Any] | None) -> tuple[datetime, str] | None:
    if not isinstance(payload, Mapping):
        return None
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    for source, value in (
        ("payload.event_time", payload.get("event_time")),
        ("payload.recorded_at", payload.get("recorded_at")),
        ("payload.created_at", payload.get("created_at")),
        ("payload.timestamp", payload.get("timestamp")),
        ("payload.time", payload.get("time")),
        ("metadata.event_time", metadata.get("event_time")),
        ("metadata.recorded_at", metadata.get("recorded_at")),
        ("metadata.created_at", metadata.get("created_at")),
        ("metadata.timestamp", metadata.get("timestamp")),
        ("metadata.time", metadata.get("time")),
        ("metadata.qq_event_time_iso", metadata.get("qq_event_time_iso")),
        ("metadata.desktop_event_time_iso", metadata.get("desktop_event_time_iso")),
    ):
        parsed = _coerce_event_datetime(value)
        if parsed is not None:
            return parsed, source
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
