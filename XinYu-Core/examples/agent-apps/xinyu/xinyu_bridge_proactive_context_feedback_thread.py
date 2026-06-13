from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from xinyu_bridge_proactive_context_feedback_payload import (
    build_owner_reply_request_update,
    load_owner_reply_feedback_payload,
)
from xinyu_bridge_proactive_context_feedback_summary import owner_reply_summary_block, short_sha256_ref


def refresh_initiative_spine_after_proactive_feedback_impl(
    runtime: Any,
    *,
    trigger: str,
    checked_at: str | None = None,
    timestamp_or_now_iso_func: Callable[..., str],
    run_initiative_spine_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    checked_at = timestamp_or_now_iso_func(checked_at)
    try:
        return run_initiative_spine_func(
            runtime.xinyu_dir,
            checked_at=checked_at,
            trigger=trigger,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] initiative spine feedback refresh failed: {exc}", flush=True)
        return {"accepted": False, "notes": [f"initiative_spine_feedback_error:{type(exc).__name__}"]}


def mark_proactive_owner_reply_impl(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    reply: str,
    read_text_safe_func: Callable[..., str],
    state_field_func: Callable[..., str],
    timestamp_or_now_iso_func: Callable[..., str],
    safe_str_func: Callable[..., str],
    atomic_write_text_func: Callable[..., None],
    append_proactive_lifecycle_event_func: Callable[..., None],
    owner_reply_preview_func: Callable[..., str],
) -> bool:
    feedback = load_owner_reply_feedback_payload(
        runtime,
        payload,
        read_text_safe_func=read_text_safe_func,
        state_field_func=state_field_func,
    )
    if feedback is None:
        return False

    answered_at = datetime.now().astimezone().isoformat()
    updated = build_owner_reply_request_update(
        feedback.request,
        answered_at=answered_at,
        timestamp_or_now_iso_func=timestamp_or_now_iso_func,
    )
    extra = owner_reply_summary_block(
        answered_at=answered_at,
        owner_reply_preview_text=owner_reply_preview_func(text),
        owner_reply_ref=short_sha256_ref(text, safe_str_func=safe_str_func),
        xinyu_reply_ref=short_sha256_ref(reply, safe_str_func=safe_str_func),
    )
    try:
        atomic_write_text_func(feedback.request_path, updated.rstrip() + extra, final_newline=False)
    except OSError:
        return False

    append_proactive_lifecycle_event_func(
        runtime.xinyu_dir,
        event_kind="proactive_owner_reply_closed",
        event_time=answered_at,
        request_state=read_text_safe_func(feedback.request_path),
        dispatch_state=feedback.dispatch,
        request_id=feedback.request_id,
        ack_status="owner_replied",
        adapter_status="owner_reply",
        notes=["owner_reply_to_proactive", "request_answer_state_owner_replied"],
    )
    runtime._refresh_initiative_spine_after_proactive_feedback(
        trigger="owner_reply_to_proactive",
        checked_at=answered_at,
    )
    return True
