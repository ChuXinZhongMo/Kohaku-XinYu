from __future__ import annotations

from typing import Any, Callable


async def desktop_finish_proactive_ack(
    runtime: Any,
    item: dict[str, Any],
    *,
    action: str,
    status: str,
    answer_state: str,
    ack_status: str,
    notes: list[str],
    adapter_message_id: str = "",
    adapter_error: str = "",
    extra: dict[str, Any] | None = None,
    claim_id: str = "",
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    candidate_id = safe_str_func(item.get("candidateId"))
    updated = runtime._desktop_update_proactive_request_state(
        candidate_id=candidate_id,
        status=status,
        answer_state=answer_state,
        ack_status=ack_status,
        adapter_message_id=adapter_message_id,
        adapter_error=adapter_error,
        claim_id=claim_id,
    )
    event_item = (
        {**item, **updated, **(extra or {}), "desktopAction": action}
        if updated
        else {**item, **(extra or {}), "desktopAction": action}
    )
    event = await runtime._desktop_publish_proactive_delivery_item(
        event_item,
        status_override=status,
        notes=notes,
        severity="error" if status == "failed" else None,
    )
    return {
        "accepted": True,
        "ack_recorded": True,
        "candidateId": candidate_id,
        "action": action,
        "status": status,
        "eventId": safe_str_func(event.get("id")),
        **(extra or {}),
        "notes": notes + (["proactive_request_state_updated"] if updated else ["proactive_request_state_not_updated"]),
    }
