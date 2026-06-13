from __future__ import annotations

from typing import Any

import v1_canary_gate
from xinyu_bridge_semantic_fast_decision import ensure_v1_app
from xinyu_bridge_semantic_fast_decision import owner_private_semantic_fast_decision_impl
from xinyu_bridge_semantic_fast_handler import handle_owner_private_semantic_fast_turn_impl
from xinyu_bridge_semantic_fast_payloads import command_id as _command_id
from xinyu_bridge_semantic_fast_payloads import owner_private_llm_failover_context_impl
from xinyu_bridge_semantic_fast_payloads import provider_failover_context as _provider_failover_context
from xinyu_bridge_semantic_fast_payloads import safe_str as _safe_str
from xinyu_bridge_semantic_fast_payloads import timestamp_or_now_iso as _timestamp_or_now_iso
from xinyu_bridge_semantic_fast_text import (
    SEMANTIC_FAST_ALLOWED_INTENTS,
    _CONFUSION_ONLY_MARKERS,
    _OWNER_STATE_FAST_MAX_CHARS,
    _OWNER_STATE_QUESTION_MARKERS,
    _REPLY_QUALITY_COMPLAINT_MARKERS,
    _RUNTIME_STATUS_MARKERS,
    _STALE_PLAN_REPLY_MARKERS,
    _compact_text,
    _contains_any,
    _direct_greeting_ack_reply,
    _looks_like_owner_state_question,
    _ordinary_private_repair_reply,
    _repair_intents_for_text,
)
from xinyu_bridge_semantic_fast_text import empty_visible_reply_fallback_impl
from xinyu_bridge_semantic_fast_text import owner_private_direct_repair_reply_impl
from xinyu_bridge_semantic_fast_text import owner_private_empty_state_notice
from xinyu_bridge_semantic_fast_text import reply_looks_like_stale_plan_residue
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_codex_delegate import looks_like_codex_request, looks_like_owner_local_write_request


def empty_visible_reply_fallback(
    runtime: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    delegate_note: str = "",
) -> str:
    return empty_visible_reply_fallback_impl(
        runtime,
        payload=payload,
        user_text=user_text,
        delegate_note=delegate_note,
        empty_state_notice_func=owner_private_empty_state_notice,
    )


def owner_private_llm_failover_context(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
) -> dict[str, Any]:
    return owner_private_llm_failover_context_impl(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        as_bool_func=_as_bool,
        attachment_signal_func=v1_canary_gate.payload_has_attachment_signal,
        codex_request_func=looks_like_codex_request,
        local_write_request_func=looks_like_owner_local_write_request,
        safe_str_func=_safe_str,
    )


def owner_private_direct_repair_reply(runtime: Any, text: str, intents: tuple[str, ...] | None = None) -> str:
    return owner_private_direct_repair_reply_impl(
        runtime,
        text,
        intents,
        repair_intents_func=_repair_intents_for_text,
        ordinary_repair_reply_func=_ordinary_private_repair_reply,
    )


def owner_private_semantic_fast_decision(runtime: Any, payload: dict[str, Any], text: str) -> dict[str, Any]:
    return owner_private_semantic_fast_decision_impl(
        runtime,
        payload,
        text,
        ensure_v1_app_func=ensure_v1_app,
        attachment_signal_func=v1_canary_gate.payload_has_attachment_signal,
        safe_str_func=_safe_str,
        repair_intents_func=_repair_intents_for_text,
        direct_repair_reply_func=owner_private_direct_repair_reply,
        looks_like_owner_state_question_func=_looks_like_owner_state_question,
        direct_greeting_ack_reply_func=_direct_greeting_ack_reply,
        allowed_intents=SEMANTIC_FAST_ALLOWED_INTENTS,
        owner_state_fast_max_chars=_OWNER_STATE_FAST_MAX_CHARS,
    )


async def handle_owner_private_semantic_fast_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session: Any | None,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any] | None,
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
    decision: dict[str, Any] | None = None,
    record_decision_stage: bool = True,
) -> dict[str, Any] | None:
    return await handle_owner_private_semantic_fast_turn_impl(
        runtime,
        payload,
        text=text,
        session=session,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
        decision=decision,
        record_decision_stage=record_decision_stage,
        decision_func=owner_private_semantic_fast_decision,
        failover_context_func=owner_private_llm_failover_context,
        empty_state_notice_func=owner_private_empty_state_notice,
        provider_failover_context_func=_provider_failover_context,
        safe_str_func=_safe_str,
        timestamp_func=_timestamp_or_now_iso,
        command_id_func=_command_id,
    )


__all__ = [
    "SEMANTIC_FAST_ALLOWED_INTENTS",
    "empty_visible_reply_fallback",
    "ensure_v1_app",
    "handle_owner_private_semantic_fast_turn",
    "owner_private_direct_repair_reply",
    "owner_private_empty_state_notice",
    "owner_private_llm_failover_context",
    "owner_private_semantic_fast_decision",
    "reply_looks_like_stale_plan_residue",
]
