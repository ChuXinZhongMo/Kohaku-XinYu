from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_desktop_proactive_projection_labels import proactive_candidate_id, proactive_state_labels
from xinyu_bridge_desktop_proactive_projection_status import (
    proactive_claimable,
    proactive_delivery_status,
    proactive_requires_owner_ack,
    proactive_state_status,
)


def desktop_proactive_delivery_payload(
    item: dict[str, Any],
    *,
    status_override: str = "",
    notes: list[str] | tuple[str, ...] | None = None,
    safe_str: Callable[..., str],
    dedupe: Callable[..., list[Any]],
    desktop_hash: Callable[..., str],
    desktop_text_preview: Callable[..., str],
) -> dict[str, Any]:
    status = proactive_delivery_status(item, status_override=status_override, safe_str=safe_str)
    return {
        **item,
        "status": status,
        "updatedAt": datetime.now().astimezone().isoformat(),
        "claimId": safe_str(item.get("claimId")),
        "ackStatus": safe_str(item.get("ackStatus")),
        "adapterMessageHash": desktop_hash(item.get("adapterMessageId")),
        "adapterErrorPreview": desktop_text_preview(safe_str(item.get("adapterError")), limit=180),
        "notes": dedupe(list(item.get("notes", [])) + list(notes or []))[:10],
    }


def desktop_proactive_item_from_state(
    root: Path,
    *,
    include_final: bool = False,
    read_text_safe: Callable[..., str],
    state_field: Callable[..., str],
    desktop_hash: Callable[..., str],
    desktop_text_preview: Callable[..., str],
    compose_visible_message: Callable[..., str],
    recent_owner_private_turns_func: Callable[..., list[Any]],
    expired_func: Callable[[str], bool],
    inbox_statuses: set[str],
) -> dict[str, Any]:
    state = read_text_safe(root / "memory/context/proactive_request_state.md")
    if not state:
        return {}

    status = proactive_state_status(
        state,
        include_final=include_final,
        state_field=state_field,
        inbox_statuses=inbox_statuses,
        expired=expired_func,
    )
    if not status:
        return {}

    request_id = state_field(state, "request_id", "")
    question = state_field(state, "concrete_question", "")
    candidate_id = proactive_candidate_id(request_id, question, desktop_hash=desktop_hash)
    if not candidate_id:
        return {}

    delivery_level = state_field(state, "delivery_level", "none")
    return {
        "candidateId": candidate_id,
        "requestId": request_id,
        "status": status,
        "deliveryLevel": delivery_level,
        "requiresOwnerAck": proactive_requires_owner_ack(status, delivery_level),
        "claimable": proactive_claimable(status, delivery_level),
        "createdAt": state_field(state, "created_at", ""),
        "expiresAt": state_field(state, "expires_at", ""),
        "kind": state_field(state, "kind", ""),
        "source": state_field(state, "source", ""),
        "focusKind": state_field(state, "focus_kind", ""),
        "priority": state_field(state, "priority", ""),
        "requestFamily": state_field(state, "request_family", ""),
        "threadId": state_field(state, "thread_id", ""),
        "requestedAction": state_field(state, "requested_action", ""),
        "evidenceHash": state_field(state, "evidence_hash", ""),
        **proactive_state_labels(
            state,
            state_field=state_field,
            desktop_hash=desktop_hash,
            desktop_text_preview=desktop_text_preview,
            compose_visible_message=compose_visible_message,
            recent_owner_private_turns_func=recent_owner_private_turns_func,
        ),
        "answerState": state_field(state, "request_answer_state", "pending"),
        "claimId": state_field(state, "last_claim_id", ""),
        "ackStatus": state_field(state, "last_ack_status", ""),
        "adapterMessageId": state_field(state, "adapter_message_id", ""),
        "adapterError": state_field(state, "adapter_error", ""),
        "notes": [],
    }
