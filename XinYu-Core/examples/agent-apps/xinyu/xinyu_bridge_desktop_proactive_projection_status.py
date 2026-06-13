from __future__ import annotations

from typing import Any, Callable


def proactive_delivery_status(
    item: dict[str, Any],
    *,
    status_override: str = "",
    safe_str: Callable[..., str],
) -> str:
    return safe_str(status_override or item.get("status"), "unknown") or "unknown"


def proactive_state_status(
    state: str,
    *,
    include_final: bool,
    state_field: Callable[..., str],
    inbox_statuses: set[str],
    expired: Callable[[str], bool],
) -> str:
    status = state_field(state, "status", "unknown")
    expires_at = state_field(state, "expires_at", "")
    if expired(expires_at) and status in inbox_statuses:
        status = "expired"
    if not include_final and status not in inbox_statuses:
        return ""
    if include_final and status in {"", "unknown"}:
        return ""
    return status


def proactive_requires_owner_ack(status: str, delivery_level: str) -> bool:
    return status == "candidate_only" or delivery_level in {"state_only", "preview_only"}


def proactive_claimable(status: str, delivery_level: str) -> bool:
    return status == "ready" and delivery_level in {"queue_owner_private", "claim_ack"}


def desktop_apply_proactive_delivery(
    payload: dict[str, Any],
    *,
    safe_str: Callable[..., str],
    final_statuses: set[str],
    remember_history_func: Callable[[dict[str, Any]], Any],
    remove_inbox_func: Callable[[str], Any],
    upsert_inbox_func: Callable[[dict[str, Any]], Any],
) -> None:
    status = safe_str(payload.get("status"))
    candidate_id = safe_str(payload.get("candidateId"))
    if not candidate_id:
        return
    if status in final_statuses:
        remember_history_func(payload)
        remove_inbox_func(candidate_id)
        return
    upsert_inbox_func(payload)
