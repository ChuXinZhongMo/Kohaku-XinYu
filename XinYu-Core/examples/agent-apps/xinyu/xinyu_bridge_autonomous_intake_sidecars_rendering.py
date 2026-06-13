from __future__ import annotations

from typing import Any

from xinyu_bridge_values import as_bool, safe_str


def watched_source_summary(watched: dict[str, Any]) -> str | None:
    if safe_str(watched.get("status")) == "no_sources":
        return None
    return (
        "watched_source:"
        f"{safe_str(watched.get('status'), 'unknown')}/"
        f"{safe_str(watched.get('fetched_items'), '0')}/"
        f"{safe_str(watched.get('new_items'), '0')}"
    )


def github_learning_summary(github: dict[str, Any]) -> str:
    return (
        "github_learning:"
        f"{safe_str(github.get('status'), 'unknown')}/"
        f"{safe_str(github.get('candidates_found'), '0')}/"
        f"{safe_str(github.get('staged_repos'), '0')}"
    )


def daily_digest_summary(digest: dict[str, Any]) -> str:
    return (
        "daily_digest:"
        f"{safe_str(digest.get('status'), 'unknown')}/"
        f"{str(as_bool(digest.get('generated'), default=False)).lower()}"
    )


def creative_writing_summary(creative: dict[str, Any]) -> str:
    return (
        "creative_writing:"
        f"{safe_str(creative.get('status'), 'unknown')}/"
        f"{safe_str(creative.get('today_chapters_written'), '0')}/"
        f"{safe_str(creative.get('daily_target_chapters'), '0')}/"
        f"{safe_str(creative.get('total_chapters'), '0')}"
    )


def review_inbox_summary(review: dict[str, Any]) -> str:
    return (
        "review_inbox:"
        f"{safe_str(review.get('pending_count'), '0')}/"
        f"{str(as_bool(review.get('queued'), default=False)).lower()}"
    )


def goldmark_dehydrate_summary(goldmark: dict[str, Any]) -> str:
    return (
        "goldmark_dehydrate:"
        f"{safe_str(goldmark.get('status'), 'unknown')}/"
        f"{safe_str(goldmark.get('processed'), '0')}/"
        f"{safe_str(goldmark.get('succeeded'), '0')}/"
        f"{safe_str(goldmark.get('skipped'), '0')}/"
        f"{safe_str(goldmark.get('failed'), '0')}"
    )
