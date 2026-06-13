from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from xinyu_bridge_slow_live_finish_payloads import (
    build_finish_sidecars_kwargs,
    build_prepared_finish_success_kwargs,
    build_success_notes_kwargs,
    build_success_publish_kwargs,
)
from xinyu_bridge_slow_live_state import (
    SlowLiveEntryState,
    SlowLiveModelTurnState,
    SlowLivePostModelReplyState,
)


TraceRouteStage = Callable[..., Any]
FinishSidecarsRunner = Callable[..., Any]


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
    finish_sidecars_with_trace_func: Callable[..., Any],
    sidecars_runner: FinishSidecarsRunner,
    build_success_notes_func: Callable[..., list[str]],
    publish_success_func: Callable[..., Any],
) -> dict[str, Any]:
    finish_sidecars = await finish_sidecars_with_trace_func(
        runtime,
        sidecars_runner=sidecars_runner,
        trace_route_stage=trace_route_stage,
        **build_finish_sidecars_kwargs(locals()),
    )
    archive_result = finish_sidecars["archive_result"]
    after_memory = finish_sidecars["after_memory"]
    notes = build_success_notes_func(**build_success_notes_kwargs(locals()))
    return await publish_success_func(
        runtime,
        payload,
        **build_success_publish_kwargs(locals()),
    )


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
    finish_success_func: Callable[..., Any],
    model_turn_coercer: Callable[..., SlowLiveModelTurnState],
    post_model_reply_coercer: Callable[..., SlowLivePostModelReplyState],
) -> dict[str, Any]:
    model_turn_state = model_turn_coercer(model_turn)
    post_model_state = post_model_reply_coercer(post_model_reply)
    return await finish_success_func(
        runtime,
        payload,
        **build_prepared_finish_success_kwargs(locals()),
    )
