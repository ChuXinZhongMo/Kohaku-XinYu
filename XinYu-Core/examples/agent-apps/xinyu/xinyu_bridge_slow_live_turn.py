from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, Callable

import xinyu_bridge_semantic_fast_routes
import xinyu_bridge_codex_runtime
from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_reply_pipeline import render_outward_reply_with_trace
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_bridge_slow_live_state import (
    SlowLiveEntryState,
    SlowLiveMemoryRecallResult,
    SlowLiveModelContexts,
    SlowLiveModelTurnState,
    SlowLivePostModelReplyState,
    SlowLiveResponseState,
    coerce_model_turn_state as _coerce_model_turn_state,
    coerce_post_model_reply_state as _coerce_post_model_reply_state,
)
from xinyu_bridge_slow_live_finish import (
    finish_and_publish_slow_live_success_turn as _runtime_finish_and_publish_slow_live_success_turn,
    finish_prepared_slow_live_success_turn as _runtime_finish_prepared_slow_live_success_turn,
    run_slow_live_finish_sidecars_with_trace as _runtime_run_slow_live_finish_sidecars_with_trace,
)
from xinyu_bridge_slow_live_entry import enter_slow_live_route_with_trace as _runtime_enter_slow_live_route_with_trace
from xinyu_bridge_slow_live_publish import (
    build_slow_live_success_notes as _runtime_build_slow_live_success_notes,
    notes_from_sidecar as _runtime_notes_from_sidecar,
    publish_slow_live_failed_turn as _runtime_publish_slow_live_failed_turn,
    publish_slow_live_success_turn as _runtime_publish_slow_live_success_turn,
)
from xinyu_bridge_slow_live_turn_publish_bindings import (
    build_slow_live_success_notes_runtime,
    notes_from_sidecar_runtime,
    publish_slow_live_failed_turn_runtime,
    publish_slow_live_success_turn_runtime,
)
from xinyu_bridge_slow_live_model_injection import (
    create_empty_visible_retry_event as _runtime_create_empty_visible_retry_event,
    has_visible_chunks as _runtime_has_visible_chunks,
    inject_slow_live_model_event as _runtime_inject_slow_live_model_event,
    owner_private_payload_matches as _runtime_owner_private_payload_matches,
    session_output_notes as _runtime_session_output_notes,
)
from xinyu_bridge_slow_live_model_turn import (
    run_slow_live_model_turn_with_failure_publish as _runtime_run_slow_live_model_turn_with_failure_publish,
)
from xinyu_bridge_slow_live_post_model import (
    prepare_slow_live_post_model_reply_state as _runtime_prepare_slow_live_post_model_reply_state,
    prepare_slow_live_post_model_reply_state_for_turn as _runtime_prepare_slow_live_post_model_reply_state_for_turn,
)
from xinyu_bridge_slow_live_service import (
    run_slow_live_turn_from_pre_model_phase_with_trace as _runtime_run_slow_live_turn_from_pre_model_phase_with_trace,
)
from xinyu_bridge_slow_live_contexts import (
    build_slow_live_model_contexts as _runtime_build_slow_live_model_contexts,
    build_slow_live_response_state as _runtime_build_slow_live_response_state,
    observe_slow_live_persona_sidecar as _runtime_observe_slow_live_persona_sidecar,
    run_slow_live_emotion_council_shadow as _runtime_run_slow_live_emotion_council_shadow,
    run_slow_live_memory_recall as _runtime_run_slow_live_memory_recall,
)
from xinyu_bridge_slow_live_context_bindings import (
    build_slow_live_model_contexts_runtime,
    build_slow_live_response_state_runtime,
    observe_slow_live_persona_sidecar_runtime,
    run_slow_live_emotion_council_shadow_runtime,
    run_slow_live_memory_recall_runtime,
)
from xinyu_bridge_slow_live_model_bindings import (
    inject_slow_live_model_event_runtime,
    prepare_slow_live_post_model_reply_state_for_turn_runtime,
    prepare_slow_live_post_model_reply_state_runtime,
    run_slow_live_model_turn_with_failure_publish_runtime,
)
from xinyu_bridge_slow_live_finish_bindings import (
    finish_and_publish_slow_live_success_turn_runtime,
    finish_prepared_slow_live_success_turn_runtime,
    run_slow_live_finish_sidecars_with_trace_runtime,
    run_slow_live_turn_from_pre_model_phase_with_trace_runtime,
)
from xinyu_bridge_slow_live_reply_adjustment_bindings import (
    apply_slow_live_current_reference_repair_runtime,
    apply_slow_live_final_reply_guard_runtime,
    apply_slow_live_life_reply_policy_runtime,
    apply_slow_live_outward_renderer_runtime,
    apply_slow_live_reply_adjustment_pipeline_runtime,
    apply_slow_live_reply_bubble_policy_runtime,
    apply_slow_live_stale_context_repair_runtime,
    apply_slow_live_sticker_reply_override_runtime,
    apply_slow_live_style_pressure_empty_fallback_runtime,
    apply_slow_live_visible_dedupe_runtime,
    recover_slow_live_empty_visible_reply_runtime,
)
from xinyu_bridge_slow_live_reply_adjustments import (
    apply_slow_live_current_reference_repair as _runtime_apply_slow_live_current_reference_repair,
    apply_slow_live_final_reply_guard as _runtime_apply_slow_live_final_reply_guard,
    apply_slow_live_life_reply_policy as _runtime_apply_slow_live_life_reply_policy,
    apply_slow_live_outward_renderer as _runtime_apply_slow_live_outward_renderer,
    apply_slow_live_reply_bubble_policy as _runtime_apply_slow_live_reply_bubble_policy,
    apply_slow_live_reply_adjustment_pipeline as _runtime_apply_slow_live_reply_adjustment_pipeline,
    apply_slow_live_stale_context_repair as _runtime_apply_slow_live_stale_context_repair,
    apply_slow_live_sticker_reply_override as _runtime_apply_slow_live_sticker_reply_override,
    apply_slow_live_style_pressure_empty_fallback as _runtime_apply_slow_live_style_pressure_empty_fallback,
    apply_slow_live_visible_dedupe as _runtime_apply_slow_live_visible_dedupe,
    recover_slow_live_empty_visible_reply as _runtime_recover_slow_live_empty_visible_reply,
)
from xinyu_bridge_time_utils import timestamp_or_now_iso
from xinyu_bridge_turn_finish_sidecars import run_slow_turn_finish_sidecars
from xinyu_bridge_turn_pipeline import try_pre_slow_semantic_fast_route_with_trace
from xinyu_bridge_values import dedupe as _dedupe
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_continuity_handoff import build_continuity_handoff_prompt_block, refresh_continuity_handoff
from xinyu_current_reference_guard import repair_current_reference_reply
from xinyu_expression_self_learning import record_expression_self_learning_event
from xinyu_life_reply_policy import apply_life_reply_policy, build_life_reply_prompt_block
from xinyu_living_memory_recall import run_living_memory_recall_algorithm
from xinyu_emotion_council import build_emotion_council_prompt_block, run_emotion_council_shadow
from xinyu_early_visible_segment import observe_early_visible_segment_shadow
from xinyu_persona_state import observe_persona_turn
from xinyu_response_error_loop import classify_response_error
from xinyu_runtime_presence import build_runtime_presence_prompt_block
from xinyu_runtime_presence import record_turn_finished
from xinyu_scene_frame import build_scene_frame
from xinyu_sent_reply_index import visible_text_hash
from xinyu_slow_state_modulator import build_slow_state
from xinyu_turn_classifier import classify_visible_turn
from xinyu_uncertainty_pause import build_uncertainty_pause_prompt_block
from xinyu_visible_reply_guard import dedupe_visible_reply


TraceRouteStage = Callable[..., Any]
MemoryRecallRunner = Callable[..., Any]
FinishSidecarsRunner = Callable[..., Any]
EMPTY_VISIBLE_RETRY_TIMEOUT_SECONDS = 45
FALSE_SINGLE_BUBBLE_REPLY = "可以拆。你要我拆哪段，我按一条一条发。"
STYLE_PRESSURE_EMPTY_REPLY = "哪句最明显？"

def _deps() -> dict[str, Any]:
    return globals()


def _int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _session_output_notes(session: Any) -> list[str]:
    return _runtime_session_output_notes(
        session,
        safe_str_func=_safe_str,
        int_or_zero_func=_int_or_zero,
    )


def _has_visible_chunks(session: Any) -> bool:
    return _runtime_has_visible_chunks(session, safe_str_func=_safe_str)


def _owner_private_payload_matches(runtime: Any, payload: dict[str, Any]) -> bool:
    return _runtime_owner_private_payload_matches(runtime, payload)


def _create_empty_visible_retry_event(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    turn_id: str,
    session_key: str,
) -> Any:
    return _runtime_create_empty_visible_retry_event(
        runtime,
        payload=payload,
        text=text,
        turn_id=turn_id,
        session_key=session_key,
        safe_str_func=_safe_str,
    )


async def run_slow_live_memory_recall(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    session: Any,
    session_key: str,
    turn_id: str,
    visible_turn: Any,
    evaluated_at: str,
    trace_route_stage: TraceRouteStage,
    recall_runner: MemoryRecallRunner | None = None,
) -> SlowLiveMemoryRecallResult:
    return await run_slow_live_memory_recall_runtime(locals(), _deps())


async def build_slow_live_model_contexts(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    visible_turn: Any,
    recalled_context: Any,
    evaluated_at: str,
) -> SlowLiveModelContexts:
    return await build_slow_live_model_contexts_runtime(locals(), _deps())


async def publish_slow_live_failed_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session: Any,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    status: str,
    notes: list[str],
    recalled_context_event: dict[str, Any],
    recalled_context: Any,
) -> int:
    return await publish_slow_live_failed_turn_runtime(locals(), _deps())


async def publish_slow_live_success_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    reply: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: Any,
    after_memory: Any,
    notes: list[str],
    archive_result: dict[str, Any],
    recalled_context_event: dict[str, Any],
    recalled_context: Any,
    reply_bubble_force_units: list[int],
    trace_route_stage: TraceRouteStage,
) -> dict[str, Any]:
    return await publish_slow_live_success_turn_runtime(locals(), _deps())


def _notes_from_sidecar(sidecar: dict[str, Any], limit: int) -> list[str]:
    return notes_from_sidecar_runtime(sidecar, limit, _deps())


def build_slow_live_success_notes(
    *,
    reply: str,
    empty_visible_reply_no_fallback: bool,
    rendered: bool,
    renderer_reason: str,
    outward_renderer: bool,
    renderer_mode: str,
    final_guard_flags: list[str],
    final_guard_applied: bool,
    stale_context_reply_replaced: bool,
    visible_dedupe: Any,
    finish_sidecars: dict[str, Any],
    proactive_tail_synced: bool,
    model_codex_delegate_note: str,
    wait_to_think_task: str,
    curiosity_eval: dict[str, Any],
    private_thought_outcome: dict[str, Any],
    uncertainty_pause_reply: dict[str, Any],
    continuity_handoff: dict[str, Any],
    life_reply_policy: dict[str, Any],
    life_reply_adjustment: dict[str, Any],
    response_error_loop: dict[str, Any],
    slow_state_runtime: dict[str, Any],
    current_sticker_reply: str,
    recent_sticker_reply: str,
    reply_bubble_force_units: list[int],
    persona_sidecar: dict[str, Any],
    event_sidecar: dict[str, Any],
    v1_shadow: dict[str, Any],
    tinykernel_shadow: dict[str, Any],
    emotion_council: dict[str, Any],
    recalled_context_notes: list[str],
    expression_learning: dict[str, Any],
    cleanup: dict[str, Any],
    session: Any,
) -> list[str]:
    return build_slow_live_success_notes_runtime(locals(), _deps())


def observe_slow_live_persona_sidecar(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    observer: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return observe_slow_live_persona_sidecar_runtime(locals(), _deps())


def run_slow_live_emotion_council_shadow(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    checked_at: str | None = None,
    runner: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return run_slow_live_emotion_council_shadow_runtime(locals(), _deps())


async def enter_slow_live_route_with_trace(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
    trace_route_stage: TraceRouteStage,
) -> SlowLiveEntryState:
    return await _runtime_enter_slow_live_route_with_trace(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
        trace_route_stage=trace_route_stage,
        emotion_council_func=run_slow_live_emotion_council_shadow,
        semantic_fast_func=try_pre_slow_semantic_fast_route_with_trace,
    )


def build_slow_live_response_state(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    visible_turn: Any,
    recalled_context: Any,
    evaluated_at: str,
    response_classifier: Callable[..., Any] | None = None,
    scene_builder: Callable[..., Any] | None = None,
    slow_state_builder: Callable[..., Any] | None = None,
) -> SlowLiveResponseState:
    return build_slow_live_response_state_runtime(locals(), _deps())


def apply_slow_live_visible_dedupe(runtime: Any, session: Any, reply: str) -> dict[str, Any]:
    return apply_slow_live_visible_dedupe_runtime(locals(), _deps())


def apply_slow_live_stale_context_repair(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    user_text: str,
    final_guard_flags: list[str],
    blocked_by_delegate: bool,
) -> dict[str, Any]:
    return apply_slow_live_stale_context_repair_runtime(locals(), _deps())


def apply_slow_live_life_reply_policy(
    runtime: Any,
    session: Any,
    *,
    reply: str,
    user_text: str,
    life_reply_policy: dict[str, Any],
    blocked_by_delegate: bool,
) -> dict[str, Any]:
    return apply_slow_live_life_reply_policy_runtime(locals(), _deps())


def apply_slow_live_current_reference_repair(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    user_text: str,
    final_guard_flags: list[str],
    blocked_by_delegate: bool,
) -> dict[str, Any]:
    return apply_slow_live_current_reference_repair_runtime(locals(), _deps())


def apply_slow_live_reply_bubble_policy(
    runtime: Any,
    session: Any,
    *,
    reply: str,
    user_text: str,
    dialogue_tail: list[dict[str, Any]],
    final_guard_flags: list[str],
) -> dict[str, Any]:
    return apply_slow_live_reply_bubble_policy_runtime(locals(), _deps())


def apply_slow_live_sticker_reply_override(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    user_text: str,
) -> dict[str, Any]:
    return apply_slow_live_sticker_reply_override_runtime(locals(), _deps())


def apply_slow_live_style_pressure_empty_fallback(
    runtime: Any,
    session: Any,
    *,
    reply: str,
    final_guard_flags: list[str],
) -> dict[str, Any]:
    return apply_slow_live_style_pressure_empty_fallback_runtime(locals(), _deps())


async def recover_slow_live_empty_visible_reply(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    user_text: str,
    final_guard_flags: list[str],
    rendered: bool,
    renderer_reason: str,
    recalled_context: Any,
    blocked_by_delegate: bool,
) -> dict[str, Any]:
    return await recover_slow_live_empty_visible_reply_runtime(locals(), _deps())


async def apply_slow_live_final_reply_guard(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    user_text: str,
    recalled_context: Any,
    trace_route_stage: TraceRouteStage,
    codex_delegate_blocked: bool,
) -> dict[str, Any]:
    return await apply_slow_live_final_reply_guard_runtime(locals(), _deps())


async def apply_slow_live_outward_renderer(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    draft_reply: str,
    user_text: str,
    recalled_context: Any,
    trace_route_stage: TraceRouteStage,
    blocked_by_delegate: bool,
) -> dict[str, Any]:
    return await apply_slow_live_outward_renderer_runtime(locals(), _deps())


async def apply_slow_live_reply_adjustment_pipeline(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    draft_reply: str,
    user_text: str,
    recalled_context: Any,
    life_reply_policy: dict[str, Any],
    trace_route_stage: TraceRouteStage,
    blocked_by_delegate: bool,
    codex_delegate_blocked: bool,
) -> dict[str, Any]:
    return await apply_slow_live_reply_adjustment_pipeline_runtime(locals(), _deps())


async def prepare_slow_live_post_model_reply_state(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    recalled_context: Any,
    life_reply_policy: dict[str, Any],
    visible_turn: Any,
    evaluated_at: str,
    trace_route_stage: TraceRouteStage,
) -> SlowLivePostModelReplyState:
    return await prepare_slow_live_post_model_reply_state_runtime(locals(), _deps())


async def prepare_slow_live_post_model_reply_state_for_turn(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    model_turn: SlowLiveModelTurnState | Mapping[str, Any],
    evaluated_at: str,
    trace_route_stage: TraceRouteStage,
) -> SlowLivePostModelReplyState:
    return await prepare_slow_live_post_model_reply_state_for_turn_runtime(locals(), _deps())


async def inject_slow_live_model_event(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session: Any,
    event: Any,
    text: str,
    turn_id: str,
    visible_turn: Any,
    persona_sidecar: dict[str, Any],
    curiosity_eval: dict[str, Any],
    recalled_context: Any,
    runtime_presence_context: str,
    life_reply_policy: dict[str, Any],
    emotion_council_context: str,
    trace_route_stage: TraceRouteStage,
) -> None:
    await inject_slow_live_model_event_runtime(locals(), _deps())


async def run_slow_live_model_turn_with_failure_publish(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session: Any,
    text: str,
    session_key: str,
    turn_id: str,
    llm_failover_turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    turn_event_timestamp: int,
    evaluated_at: str,
    curiosity_eval: dict[str, Any],
    trace_route_stage: TraceRouteStage,
) -> SlowLiveModelTurnState:
    return await run_slow_live_model_turn_with_failure_publish_runtime(locals(), _deps())


async def run_slow_live_finish_sidecars_with_trace(
    runtime: Any,
    *,
    sidecars_runner: FinishSidecarsRunner,
    trace_route_stage: TraceRouteStage,
    **kwargs: Any,
) -> dict[str, Any]:
    return await run_slow_live_finish_sidecars_with_trace_runtime(locals(), _deps())


async def finish_and_publish_slow_live_success_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    reply: str,
    draft_reply: str,
    session: Any,
    session_key: str,
    turn_id: str,
    publish_turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    visible_turn: Any,
    final_guard_flags: list[str],
    final_guard_applied: bool,
    stale_context_reply_replaced: bool,
    expression_learning: dict[str, Any],
    recalled_context: Any,
    recalled_context_event: dict[str, Any],
    recalled_context_notes: list[str],
    private_thought_outcome: dict[str, Any],
    emotion_council: dict[str, Any],
    persona_sidecar: dict[str, Any],
    continuity_handoff: dict[str, Any],
    wait_to_think_sidecar: dict[str, Any],
    self_code_task: str,
    direct_codex_task: str,
    model_codex_task: str,
    wait_to_think_task: str,
    model_codex_delegate_note: str,
    empty_visible_reply_no_fallback: bool,
    rendered: bool,
    renderer_reason: str,
    visible_dedupe: Any,
    proactive_tail_synced: bool,
    curiosity_eval: dict[str, Any],
    uncertainty_pause_reply: dict[str, Any],
    life_reply_policy: dict[str, Any],
    life_reply_adjustment: dict[str, Any],
    response_error_loop: dict[str, Any],
    slow_state_runtime: dict[str, Any],
    current_sticker_reply: str,
    recent_sticker_reply: str,
    reply_bubble_force_units: list[str],
    event_sidecar: dict[str, Any],
    v1_shadow: dict[str, Any],
    tinykernel_shadow: dict[str, Any],
    cleanup: dict[str, Any],
    trace_route_stage: TraceRouteStage,
) -> dict[str, Any]:
    return await finish_and_publish_slow_live_success_turn_runtime(locals(), _deps())


async def finish_prepared_slow_live_success_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    publish_turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    pre_model_phase: Mapping[str, Any],
    slow_live_entry: SlowLiveEntryState | Mapping[str, Any],
    model_turn: SlowLiveModelTurnState | Mapping[str, Any],
    post_model_reply: SlowLivePostModelReplyState | Mapping[str, Any],
    cleanup: dict[str, Any],
    trace_route_stage: TraceRouteStage,
) -> dict[str, Any]:
    return await finish_prepared_slow_live_success_turn_runtime(locals(), _deps())


async def run_slow_live_turn_from_pre_model_phase_with_trace(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    publish_turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    turn_event_time: str,
    turn_event_timestamp: int,
    pre_model_phase: Mapping[str, Any],
    cleanup: dict[str, Any],
    settle_seconds: float,
    trace_route_stage: TraceRouteStage,
) -> dict[str, Any]:
    return await run_slow_live_turn_from_pre_model_phase_with_trace_runtime(locals(), _deps())

__all__ = (
    "Any",
    "BridgeRequestError",
    "Callable",
    "EMPTY_VISIBLE_RETRY_TIMEOUT_SECONDS",
    "FALSE_SINGLE_BUBBLE_REPLY",
    "FinishSidecarsRunner",
    "HTTPStatus",
    "Mapping",
    "MemoryRecallRunner",
    "STYLE_PRESSURE_EMPTY_REPLY",
    "SlowLiveEntryState",
    "SlowLiveMemoryRecallResult",
    "SlowLiveModelContexts",
    "SlowLiveModelTurnState",
    "SlowLivePostModelReplyState",
    "SlowLiveResponseState",
    "TraceRouteStage",
    "_coerce_model_turn_state",
    "_coerce_post_model_reply_state",
    "_create_empty_visible_retry_event",
    "_dedupe",
    "_deps",
    "_has_visible_chunks",
    "_int_or_zero",
    "_notes_from_sidecar",
    "_owner_private_payload_matches",
    "_runtime_apply_slow_live_current_reference_repair",
    "_runtime_apply_slow_live_final_reply_guard",
    "_runtime_apply_slow_live_life_reply_policy",
    "_runtime_apply_slow_live_outward_renderer",
    "_runtime_apply_slow_live_reply_adjustment_pipeline",
    "_runtime_apply_slow_live_reply_bubble_policy",
    "_runtime_apply_slow_live_stale_context_repair",
    "_runtime_apply_slow_live_sticker_reply_override",
    "_runtime_apply_slow_live_style_pressure_empty_fallback",
    "_runtime_apply_slow_live_visible_dedupe",
    "_runtime_build_slow_live_model_contexts",
    "_runtime_build_slow_live_response_state",
    "_runtime_build_slow_live_success_notes",
    "_runtime_create_empty_visible_retry_event",
    "_runtime_enter_slow_live_route_with_trace",
    "_runtime_finish_and_publish_slow_live_success_turn",
    "_runtime_finish_prepared_slow_live_success_turn",
    "_runtime_has_visible_chunks",
    "_runtime_inject_slow_live_model_event",
    "_runtime_notes_from_sidecar",
    "_runtime_observe_slow_live_persona_sidecar",
    "_runtime_owner_private_payload_matches",
    "_runtime_prepare_slow_live_post_model_reply_state",
    "_runtime_prepare_slow_live_post_model_reply_state_for_turn",
    "_runtime_publish_slow_live_failed_turn",
    "_runtime_publish_slow_live_success_turn",
    "_runtime_recover_slow_live_empty_visible_reply",
    "_runtime_run_slow_live_emotion_council_shadow",
    "_runtime_run_slow_live_finish_sidecars_with_trace",
    "_runtime_run_slow_live_memory_recall",
    "_runtime_run_slow_live_model_turn_with_failure_publish",
    "_runtime_run_slow_live_turn_from_pre_model_phase_with_trace",
    "_runtime_session_output_notes",
    "_safe_str",
    "_session_output_notes",
    "annotations",
    "apply_life_reply_policy",
    "apply_slow_live_current_reference_repair",
    "apply_slow_live_current_reference_repair_runtime",
    "apply_slow_live_final_reply_guard",
    "apply_slow_live_final_reply_guard_runtime",
    "apply_slow_live_life_reply_policy",
    "apply_slow_live_life_reply_policy_runtime",
    "apply_slow_live_outward_renderer",
    "apply_slow_live_outward_renderer_runtime",
    "apply_slow_live_reply_adjustment_pipeline",
    "apply_slow_live_reply_adjustment_pipeline_runtime",
    "apply_slow_live_reply_bubble_policy",
    "apply_slow_live_reply_bubble_policy_runtime",
    "apply_slow_live_stale_context_repair",
    "apply_slow_live_stale_context_repair_runtime",
    "apply_slow_live_sticker_reply_override",
    "apply_slow_live_sticker_reply_override_runtime",
    "apply_slow_live_style_pressure_empty_fallback",
    "apply_slow_live_style_pressure_empty_fallback_runtime",
    "apply_slow_live_visible_dedupe",
    "apply_slow_live_visible_dedupe_runtime",
    "asyncio",
    "build_continuity_handoff_prompt_block",
    "build_emotion_council_prompt_block",
    "build_life_reply_prompt_block",
    "build_runtime_presence_prompt_block",
    "build_scene_frame",
    "build_slow_live_model_contexts",
    "build_slow_live_model_contexts_runtime",
    "build_slow_live_response_state",
    "build_slow_live_response_state_runtime",
    "build_slow_live_success_notes",
    "build_slow_live_success_notes_runtime",
    "build_slow_state",
    "build_uncertainty_pause_prompt_block",
    "classify_response_error",
    "classify_visible_turn",
    "dedupe_visible_reply",
    "enter_slow_live_route_with_trace",
    "finish_and_publish_slow_live_success_turn",
    "finish_and_publish_slow_live_success_turn_runtime",
    "finish_prepared_slow_live_success_turn",
    "finish_prepared_slow_live_success_turn_runtime",
    "inject_slow_live_model_event",
    "inject_slow_live_model_event_runtime",
    "normalize_bridge_reply",
    "notes_from_sidecar_runtime",
    "observe_early_visible_segment_shadow",
    "observe_persona_turn",
    "observe_slow_live_persona_sidecar",
    "observe_slow_live_persona_sidecar_runtime",
    "prepare_slow_live_post_model_reply_state",
    "prepare_slow_live_post_model_reply_state_for_turn",
    "prepare_slow_live_post_model_reply_state_for_turn_runtime",
    "prepare_slow_live_post_model_reply_state_runtime",
    "publish_slow_live_failed_turn",
    "publish_slow_live_failed_turn_runtime",
    "publish_slow_live_success_turn",
    "publish_slow_live_success_turn_runtime",
    "record_expression_self_learning_event",
    "record_turn_finished",
    "recover_slow_live_empty_visible_reply",
    "recover_slow_live_empty_visible_reply_runtime",
    "refresh_continuity_handoff",
    "render_outward_reply_with_trace",
    "repair_current_reference_reply",
    "run_emotion_council_shadow",
    "run_living_memory_recall_algorithm",
    "run_slow_live_emotion_council_shadow",
    "run_slow_live_emotion_council_shadow_runtime",
    "run_slow_live_finish_sidecars_with_trace",
    "run_slow_live_finish_sidecars_with_trace_runtime",
    "run_slow_live_memory_recall",
    "run_slow_live_memory_recall_runtime",
    "run_slow_live_model_turn_with_failure_publish",
    "run_slow_live_model_turn_with_failure_publish_runtime",
    "run_slow_live_turn_from_pre_model_phase_with_trace",
    "run_slow_live_turn_from_pre_model_phase_with_trace_runtime",
    "run_slow_turn_finish_sidecars",
    "time",
    "timestamp_or_now_iso",
    "try_pre_slow_semantic_fast_route_with_trace",
    "visible_text_hash",
    "xinyu_bridge_codex_runtime",
    "xinyu_bridge_semantic_fast_routes",
)
