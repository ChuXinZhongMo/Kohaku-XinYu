from __future__ import annotations

from typing import Any, Callable


DESKTOP_PROACTIVE_INBOX_MAX = 50
DESKTOP_PROACTIVE_INBOX_STATUSES = {"ready", "candidate_only", "claimed"}
DESKTOP_PROACTIVE_FINAL_STATUSES = {
    "sent",
    "answered",
    "failed",
    "expired",
    "blocked",
    "none",
    "read_locally",
    "replied",
    "dismissed",
    "queued_qq",
}


def desktop_proactive_candidate_id(item: dict[str, Any], *, safe_str: Callable[..., str]) -> str:
    return safe_str(item.get("candidateId"))


def copy_desktop_proactive_item(
    inbox: dict[str, dict[str, Any]],
    candidate_id: str,
) -> dict[str, Any]:
    return dict(inbox.get(candidate_id, {}))


def merged_desktop_proactive_item(
    existing: dict[str, Any],
    item: dict[str, Any],
) -> dict[str, Any]:
    return {**existing, **dict(item)}


def desktop_proactive_non_initiative_ids(
    inbox: dict[str, dict[str, Any]],
    *,
    safe_str: Callable[..., str],
) -> list[str]:
    return [
        candidate_id
        for candidate_id, item in inbox.items()
        if safe_str(item.get("source")) != "initiative_orchestrator"
    ]


def desktop_proactive_prunable_ids(
    inbox: dict[str, dict[str, Any]],
    *,
    safe_str: Callable[..., str],
    expired: Callable[[str], bool],
    final_statuses: set[str] = DESKTOP_PROACTIVE_FINAL_STATUSES,
) -> list[str]:
    return [
        candidate_id
        for candidate_id, item in inbox.items()
        if safe_str(item.get("status")) in final_statuses or expired(safe_str(item.get("expiresAt")))
    ]
