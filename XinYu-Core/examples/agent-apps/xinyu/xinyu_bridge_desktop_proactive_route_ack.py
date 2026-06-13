from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable

from xinyu_bridge_desktop_proactive_payloads import normalize_desktop_proactive_ack_payload
from xinyu_bridge_errors import BridgeRequestError


_ACK_FINISH_BY_ACTION: dict[str, dict[str, Any]] = {
    "read_locally": {
        "status": "read_locally",
        "answer_state": "read_locally",
        "ack_status": "read_locally",
        "notes": ["desktop_read_locally"],
    },
    "dismiss": {
        "status": "dismissed",
        "answer_state": "dismissed",
        "ack_status": "dismissed",
        "notes": ["desktop_dismissed"],
    },
    "reply": {
        "status": "answered",
        "answer_state": "owner_replied",
        "ack_status": "replied",
        "notes": ["desktop_owner_replied_to_proactive"],
    },
}


async def desktop_proactive_ack(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    safe_str: Callable[..., str],
    ensure_payload_func: Callable[[dict[str, Any] | None], dict[str, Any]],
    ack_actions: set[str],
) -> dict[str, Any]:
    if runtime._closed:
        raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")

    candidate_id, action = normalize_desktop_proactive_ack_payload(
        payload,
        safe_str=safe_str,
        ensure_payload_func=ensure_payload_func,
        ack_actions=ack_actions,
    )
    item = runtime._desktop_proactive_item_from_state(include_final=True)
    if not item:
        item = runtime._desktop_proactive_existing(candidate_id)
    if not item or safe_str(item.get("candidateId")) != candidate_id:
        raise BridgeRequestError(HTTPStatus.NOT_FOUND, "desktop proactive candidate not found")

    runtime._record_desktop_initiative_feedback(item, action=action)
    if action == "approve_qq":
        return await runtime._desktop_approve_proactive_qq(item)

    finish = _ACK_FINISH_BY_ACTION[action]
    return await runtime._desktop_finish_proactive_ack(
        item,
        action=action,
        status=finish["status"],
        answer_state=finish["answer_state"],
        ack_status=finish["ack_status"],
        notes=list(finish["notes"]),
    )
