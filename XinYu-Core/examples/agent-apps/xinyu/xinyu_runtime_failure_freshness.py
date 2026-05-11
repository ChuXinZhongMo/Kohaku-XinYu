from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Mapping


RECENT_RUNTIME_FAILURE_SECONDS = 6 * 60 * 60

_FAILURE_COUNT_SIGNAL_RE = re.compile(
    r"\b(?:failure_count|failed_count|dead_count|recent_failed_count|recent_dead_count)=[1-9]"
)
_INLINE_FIELD_RE = re.compile(r"\b([A-Za-z0-9_]+)=([^\s]+)")


def parse_inline_fields(text: Any) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key, value in _INLINE_FIELD_RE.findall(_one_line(text)):
        fields[key] = _one_line(value)
    return fields


def runtime_failure_detail_active(
    detail: Any,
    *,
    checked_at: str,
    max_age_seconds: int = RECENT_RUNTIME_FAILURE_SECONDS,
) -> bool:
    text = _one_line(detail)
    if not _FAILURE_COUNT_SIGNAL_RE.search(text):
        return False
    return runtime_failure_counts_active(
        parse_inline_fields(text),
        checked_at=checked_at,
        max_age_seconds=max_age_seconds,
    )


def runtime_failure_counts_active(
    fields: Mapping[str, Any],
    *,
    checked_at: str,
    max_age_seconds: int = RECENT_RUNTIME_FAILURE_SECONDS,
) -> bool:
    failure = _safe_int(fields.get("failure_count"), 0)
    failed = _safe_int(fields.get("failed_count"), 0)
    dead = _safe_int(fields.get("dead_count"), 0)
    recent_failed = _safe_int(fields.get("recent_failed_count"), 0)
    recent_dead = _safe_int(fields.get("recent_dead_count"), 0)
    if failure > 0 or recent_failed > 0 or recent_dead > 0:
        return True
    if failed > 0:
        stamp = fields.get("last_failed_at", "")
        return not _meaningful(stamp) or _recent_enough(
            stamp,
            checked_at,
            max_age_seconds=max_age_seconds,
        )
    if dead > 0:
        return _recent_enough(
            fields.get("last_dead_at", ""),
            checked_at,
            max_age_seconds=max_age_seconds,
        )
    return False


def codex_delegate_failure_active(
    fields_or_detail: Mapping[str, Any] | Any,
    *,
    checked_at: str,
    max_age_seconds: int = RECENT_RUNTIME_FAILURE_SECONDS,
) -> bool:
    fields = (
        fields_or_detail
        if isinstance(fields_or_detail, Mapping)
        else parse_inline_fields(fields_or_detail)
    )
    stamp = fields.get("updated_at") or fields.get("codex_updated_at") or ""
    return not _meaningful(stamp) or _recent_enough(
        stamp,
        checked_at,
        max_age_seconds=max_age_seconds,
    )


def _recent_enough(value: Any, checked_at: str, *, max_age_seconds: int) -> bool:
    age = _seconds_between(_one_line(value), checked_at)
    return age is not None and 0 <= age <= max_age_seconds


def _seconds_between(start: str, end: str) -> float | None:
    start_dt = _parse_iso(start)
    end_dt = _parse_iso(end)
    if start_dt is None or end_dt is None:
        return None
    return (end_dt - start_dt).total_seconds()


def _parse_iso(value: Any) -> datetime | None:
    text = _one_line(value)
    if not text or text == "none":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _meaningful(value: Any) -> bool:
    text = _one_line(value).lower()
    return text not in {"", "none", "unknown", "false", "null"}


def _one_line(value: Any) -> str:
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default
