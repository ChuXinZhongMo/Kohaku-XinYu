from __future__ import annotations

from typing import Any

from xinyu_bridge_time_utils import timestamp_or_now_iso


def watched_source_kwargs(runtime: Any, *, checked_at: str) -> dict[str, Any]:
    return {
        "checked_at": checked_at,
        "min_interval_seconds": runtime.autonomous_maintenance_interval_seconds,
    }


def github_learning_kwargs(runtime: Any, *, checked_at: str) -> dict[str, Any]:
    return {
        "checked_at": checked_at,
        "mode": "autonomous_maintenance_github_learning",
        "max_stage": 1,
        "min_interval_seconds": max(runtime.autonomous_maintenance_interval_seconds, 21600),
    }


def daily_digest_kwargs(*, checked_at: str) -> dict[str, Any]:
    return {"observed_at": timestamp_or_now_iso(checked_at)}


def creative_writing_kwargs(*, checked_at: str) -> dict[str, Any]:
    return {
        "checked_at": checked_at,
        "daily_target": 3,
    }


def review_inbox_kwargs(runtime: Any) -> dict[str, Any]:
    return {
        "owner_user_id": runtime._owner_private_user_id(),
        "max_items": 3,
        "enqueue": False,
        "reason": "autonomous_maintenance",
    }


def goldmark_dehydrate_kwargs() -> dict[str, Any]:
    return {
        "limit": 5,
        "provider": "auto",
        "timeout_seconds": 45,
    }
