from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable


OWNER_REPLY_ACTIVE_STATUSES = {"claimed", "sent", "queued_qq"}
OWNER_REPLY_ANSWERABLE_STATES = {
    "pending",
    "",
    "unknown",
    "sent_waiting_owner_reply",
    "waiting_owner_reply",
    "sent_waiting_feedback",
}
OWNER_REPLY_DELIVERY_LEVELS = {"queue_owner_private", "claim_ack"}
OWNER_REPLY_SENT_ACK_STATUSES = {"sent", "delivered", "acked", "success"}
UNKNOWN_REQUEST_IDS = {"", "none", "unknown"}


@dataclass(frozen=True, slots=True)
class OwnerReplyFeedbackPayload:
    request_path: Any
    request: str
    dispatch: str
    request_id: str


def load_owner_reply_feedback_payload(
    runtime: Any,
    payload: dict[str, Any],
    *,
    read_text_safe_func: Callable[..., str],
    state_field_func: Callable[..., str],
) -> OwnerReplyFeedbackPayload | None:
    if not runtime._owner_private_payload_matches(payload):
        return None

    request_path = runtime.xinyu_dir / "memory/context/proactive_request_state.md"
    request = read_text_safe_func(request_path)
    if state_field_func(request, "status") not in OWNER_REPLY_ACTIVE_STATUSES:
        return None
    if state_field_func(request, "delivery_level") not in OWNER_REPLY_DELIVERY_LEVELS:
        return None
    if state_field_func(request, "request_answer_state", "pending") not in OWNER_REPLY_ANSWERABLE_STATES:
        return None

    dispatch = read_text_safe_func(runtime.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
    request_ack_status = state_field_func(request, "last_ack_status")
    dispatch_sent = state_field_func(dispatch, "last_claim_status") == "sent"
    request_sent = request_ack_status in OWNER_REPLY_SENT_ACK_STATUSES
    if not dispatch_sent and not request_sent:
        return None

    request_id = state_field_func(request, "request_id")
    dispatch_request_id = state_field_func(dispatch, "proactive_request_id")
    if (
        dispatch_sent
        and request_id not in UNKNOWN_REQUEST_IDS
        and dispatch_request_id not in UNKNOWN_REQUEST_IDS
        and request_id != dispatch_request_id
    ):
        return None

    return OwnerReplyFeedbackPayload(
        request_path=request_path,
        request=request,
        dispatch=dispatch,
        request_id=request_id,
    )


def build_owner_reply_request_update(
    request: str,
    *,
    answered_at: str,
    timestamp_or_now_iso_func: Callable[..., str],
) -> str:
    updated = re.sub(
        r"(?m)^-\s+request_answer_state:\s*.*$",
        "- request_answer_state: owner_replied",
        request,
        count=1,
    )
    if updated == request:
        updated = request.rstrip() + "\n- request_answer_state: owner_replied\n"
    updated = re.sub(
        r"(?m)^-\s+status:\s*.*$",
        "- status: answered",
        updated,
        count=1,
    )
    return re.sub(
        r"(?m)^updated_at:\s*.*$",
        f"updated_at: {timestamp_or_now_iso_func(answered_at)}",
        updated,
        count=1,
    )
