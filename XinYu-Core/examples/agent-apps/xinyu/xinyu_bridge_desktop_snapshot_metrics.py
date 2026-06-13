from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


_INITIATIVE_METRIC_FIELDS = (
    ("windowHours", "window_hours"),
    ("eventCount24h", "event_count_24h"),
    ("desktopShown24h", "desktop_shown_count_24h"),
    ("heldPrivate24h", "held_private_count_24h"),
    ("blocked24h", "blocked_count_24h"),
    ("feedbackCount24h", "feedback_count_24h"),
    ("dismissCount24h", "dismiss_count_24h"),
    ("replyCount24h", "reply_count_24h"),
    ("approvedQqCount24h", "approved_qq_count_24h"),
    ("failedCount24h", "failed_count_24h"),
    ("pendingFeedbackCount", "pending_feedback_count"),
)

_CREATIVE_STATE_FIELDS = (
    ("creative_writing_status", "status", "unknown", False),
    ("creative_writing_mode", "creative_writing_mode", "novel_mode", False),
    ("creative_writing_project", "current_project", "", False),
    ("creative_writing_today_chapters", "today_chapters_written", "0", True),
    ("creative_writing_daily_target", "daily_target_chapters", "0", True),
    ("creative_writing_min_platform_chars", "min_platform_chars", "0", True),
    ("creative_writing_target_platform_chars", "target_platform_chars", "0", True),
    ("creative_writing_total_chapters", "total_chapters", "0", True),
    ("creative_writing_publish_ready_chapters", "publish_ready_chapters", "0", True),
    ("creative_writing_publish_pending_chapters", "publish_pending_chapters", "0", True),
    ("creative_writing_latest_chapter", "latest_chapter_path", "", False),
    ("creative_writing_publication_latest_chapter", "publication_latest_chapter_path", "", False),
    ("creative_writing_publication_log", "publication_log_path", "", False),
    ("creative_writing_next_action", "next_action", "", False),
    ("creative_writing_reference_status", "reference_collection_status", "", False),
    ("creative_writing_reference_sources", "reference_sources_collected", "0", True),
    ("creative_writing_reference_downloads", "reference_downloaded_sources", "0", True),
    ("creative_writing_reference_digest", "reference_digest_path", "", False),
    ("creative_writing_reference_local_files", "reference_local_files", "0", True),
    ("creative_writing_reference_local_index", "reference_local_index_path", "", False),
)


def desktop_metric_int(value: Any, *, safe_str_func: Callable[..., str]) -> int:
    try:
        return max(0, int(safe_str_func(value).strip()))
    except (TypeError, ValueError):
        return 0


def desktop_initiative_metrics_summary(
    metrics: dict[str, Any],
    *,
    safe_str_func: Callable[..., str],
    metric_int_func: Callable[[Any], int],
) -> dict[str, Any]:
    if not metrics or safe_str_func(metrics.get("observed")) == "false":
        return {"observed": False}
    summary: dict[str, Any] = {
        "observed": True,
        "updatedAt": safe_str_func(metrics.get("updated_at")),
    }
    for public_key, source_key in _INITIATIVE_METRIC_FIELDS:
        summary[public_key] = metric_int_func(metrics.get(source_key))
    return summary


def desktop_creative_writing_state(
    root: Path,
    *,
    creative_writing_state_rel: Path,
    read_text_safe_func: Callable[[Path], str],
    state_field_func: Callable[[str, str, str], str],
    metric_int_func: Callable[[Any], int],
) -> dict[str, Any]:
    text = read_text_safe_func(root / creative_writing_state_rel)
    state: dict[str, Any] = {}
    for public_key, source_key, default, is_metric in _CREATIVE_STATE_FIELDS:
        value = state_field_func(text, source_key, default)
        state[public_key] = metric_int_func(value) if is_metric else value
    return state
