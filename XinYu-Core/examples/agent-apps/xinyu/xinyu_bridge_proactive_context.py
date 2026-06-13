from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

from xinyu_bridge_payload_policy import owner_private_payload_matches
from xinyu_bridge_proactive_context_feedback import (
    OWNER_REPLY_PREVIEW_KEEP_MARKERS,
    mark_proactive_owner_reply_impl as _mark_proactive_owner_reply_impl,
    one_line_preview as _one_line_preview_impl,
    owner_reply_preview as _owner_reply_preview_impl,
    refresh_initiative_spine_after_proactive_feedback_impl as _refresh_initiative_spine_after_proactive_feedback_impl,
)
from xinyu_bridge_proactive_context_state_store import write_proactive_request_state_text
from xinyu_bridge_proactive_context_tail import (
    append_assistant_to_dialogue_tail_impl as _append_assistant_to_dialogue_tail_impl,
    owner_private_payload_impl as _owner_private_payload_impl,
    sync_recent_proactive_to_dialogue_tail_impl as _sync_recent_proactive_to_dialogue_tail_impl,
)
from xinyu_bridge_proactive_context_thread import proactive_thread_context_impl as _proactive_thread_context_impl
from xinyu_bridge_state_text import read_text_safe, seconds_since_iso, state_field
from xinyu_bridge_time_utils import timestamp_or_now_iso
from xinyu_bridge_values import safe_str
from xinyu_dialogue_working_memory import load_dialogue_tail, save_dialogue_tail
from xinyu_initiative_spine import run_initiative_spine
from xinyu_proactive_lifecycle_trace import append_proactive_lifecycle_event
from xinyu_text_variants import readable_markers


def owner_private_payload(runtime: Any, *, source: str, message_id: str = "") -> dict[str, Any]:
    return _owner_private_payload_impl(runtime, source=source, message_id=message_id)


def append_assistant_to_dialogue_tail(
    runtime: Any,
    session_key: str,
    message: str,
    *,
    recorded_at: str = "",
) -> bool:
    return _append_assistant_to_dialogue_tail_impl(
        runtime,
        session_key,
        message,
        recorded_at=recorded_at,
        safe_str_func=safe_str,
        load_dialogue_tail_func=load_dialogue_tail,
        save_dialogue_tail_func=save_dialogue_tail,
    )


def sync_recent_proactive_to_dialogue_tail(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
) -> bool:
    return _sync_recent_proactive_to_dialogue_tail_impl(
        runtime,
        session,
        payload,
        read_text_safe_func=read_text_safe,
        state_field_func=state_field,
        seconds_since_iso_func=seconds_since_iso,
        safe_str_func=safe_str,
        save_dialogue_tail_func=save_dialogue_tail,
    )


def proactive_thread_context(runtime: Any, payload: dict[str, Any], current_text: str) -> str:
    return _proactive_thread_context_impl(
        runtime,
        payload,
        current_text,
        owner_private_payload_matches_func=owner_private_payload_matches,
        read_text_safe_func=read_text_safe,
        state_field_func=state_field,
        seconds_since_iso_func=seconds_since_iso,
        safe_str_func=safe_str,
    )


def _one_line_preview(value: Any, *, limit: int = 180) -> str:
    return _one_line_preview_impl(value, limit=limit, safe_str_func=safe_str)


def _owner_reply_preview(value: Any) -> str:
    return _owner_reply_preview_impl(
        value,
        keep_markers=OWNER_REPLY_PREVIEW_KEEP_MARKERS,
        safe_str_func=safe_str,
        one_line_preview_func=_one_line_preview,
    )


def refresh_initiative_spine_after_proactive_feedback(
    runtime: Any,
    *,
    trigger: str,
    checked_at: str | None = None,
) -> dict[str, Any]:
    return _refresh_initiative_spine_after_proactive_feedback_impl(
        runtime,
        trigger=trigger,
        checked_at=checked_at,
        timestamp_or_now_iso_func=timestamp_or_now_iso,
        run_initiative_spine_func=run_initiative_spine,
    )


def mark_proactive_owner_reply(runtime: Any, payload: dict[str, Any], *, text: str, reply: str) -> bool:
    return _mark_proactive_owner_reply_impl(
        runtime,
        payload,
        text=text,
        reply=reply,
        read_text_safe_func=read_text_safe,
        state_field_func=state_field,
        timestamp_or_now_iso_func=timestamp_or_now_iso,
        safe_str_func=safe_str,
        atomic_write_text_func=write_proactive_request_state_text,
        append_proactive_lifecycle_event_func=append_proactive_lifecycle_event,
        owner_reply_preview_func=_owner_reply_preview,
    )
