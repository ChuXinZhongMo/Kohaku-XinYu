from __future__ import annotations

from typing import Any, Callable


def ready_proactive_outbox_candidate(
    runtime: Any,
    *,
    read_text_safe_func: Callable[..., str],
    state_field_func: Callable[[str, str], str],
) -> str:
    state = read_text_safe_func(runtime.xinyu_dir / "memory/context/proactive_request_state.md")
    if state_field_func(state, "status") != "ready":
        return ""
    if state_field_func(state, "delivery_level") not in {"queue_owner_private", "claim_ack"}:
        return ""
    candidate = state_field_func(state, "concrete_question")
    return candidate if candidate not in {"", "none", "unknown"} else ""


def proactive_candidate_already_handled(
    runtime: Any,
    candidate: str,
    *,
    read_text_safe_func: Callable[..., str],
    state_field_func: Callable[[str, str], str],
) -> bool:
    state = read_text_safe_func(runtime.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
    status = state_field_func(state, "last_claim_status")
    if status not in {"claimed", "sent"}:
        return False
    return state_field_func(state, "last_claimed_message") == candidate


def record_proactive_outbound_dialogue(
    runtime: Any,
    ack_payload: dict[str, Any],
    *,
    read_text_safe_func: Callable[..., str],
    state_field_func: Callable[[str, str], str],
    timestamp_or_now_iso_func: Callable[..., str],
    safe_str_func: Callable[..., str],
    archive_message_func: Callable[..., Any],
) -> None:
    dispatch = read_text_safe_func(runtime.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
    if state_field_func(dispatch, "last_ack_status") != "sent":
        return
    message = state_field_func(dispatch, "last_claimed_message")
    if not message or message in {"none", "unknown"}:
        return

    claimed_at = timestamp_or_now_iso_func(state_field_func(dispatch, "last_claimed_at"))
    payload = runtime._owner_private_payload(
        source="proactive_request_outbox",
        message_id=safe_str_func(ack_payload.get("message_id")),
    )
    appended = runtime._append_assistant_to_dialogue_tail(
        payload["session_id"],
        message,
        recorded_at=timestamp_or_now_iso_func(claimed_at),
    )
    if not appended:
        return
    try:
        archive_message_func(
            runtime.xinyu_dir,
            payload,
            role="assistant",
            text=message,
            created_at=timestamp_or_now_iso_func(claimed_at),
            message_type="private_proactive",
            metadata={"source": "proactive_request_outbox"},
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] proactive outbound archive failed: {exc}", flush=True)
