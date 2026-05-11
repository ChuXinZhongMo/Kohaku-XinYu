from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from xinyu_runtime_failure_freshness import RECENT_RUNTIME_FAILURE_SECONDS


OUTBOX_STATUSES = ("queued", "claimed", "sent", "failed", "dead")


def summarize_outbox_items(items: list[dict[str, Any]], *, now: datetime | None = None) -> dict[str, Any]:
    checked_at = now or datetime.now().astimezone()
    counts = {status: 0 for status in OUTBOX_STATUSES}
    recent_counts = {"failed": 0, "dead": 0}
    latest_times = {"failed": "", "dead": ""}
    for item in items:
        status = safe_status(item.get("status"))
        if status in counts:
            counts[status] += 1
        if status not in latest_times:
            continue
        stamp = status_stamp(item)
        if stamp and (not latest_times[status] or stamp > latest_times[status]):
            latest_times[status] = stamp
        parsed = parse_outbox_time(stamp)
        if parsed is None:
            continue
        age = max(0.0, (checked_at - parsed.astimezone()).total_seconds())
        if age <= RECENT_RUNTIME_FAILURE_SECONDS:
            recent_counts[status] += 1
    return {
        "queue_items": sum(counts.values()),
        "queued_count": counts["queued"],
        "claimed_count": counts["claimed"],
        "sent_count": counts["sent"],
        "failed_count": counts["failed"],
        "dead_count": counts["dead"],
        "recent_failed_count": recent_counts["failed"],
        "recent_dead_count": recent_counts["dead"],
        "last_failed_at": latest_times["failed"] or "none",
        "last_dead_at": latest_times["dead"] or "none",
    }


def status_stamp(item: dict[str, Any]) -> str:
    return _safe_str(
        item.get("updated_at")
        or item.get("acked_at")
        or item.get("claimed_at")
        or item.get("created_at")
    )


def safe_status(value: Any) -> str:
    return re.sub(r"\s+", " ", _safe_str(value, "queued")).strip().lower() or "queued"


def parse_outbox_time(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text or text == "none":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)
