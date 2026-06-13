from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from xinyu_bridge_slow_live_publish import build_slow_live_success_notes, publish_slow_live_success_turn
from xinyu_bridge_slow_live_finish_service import (
    finish_and_publish_slow_live_success_turn as _finish_and_publish_slow_live_success_turn,
)
from xinyu_bridge_slow_live_finish_service import (
    finish_prepared_slow_live_success_turn as _finish_prepared_slow_live_success_turn,
)
from xinyu_bridge_slow_live_state import (
    SlowLiveEntryState,
    SlowLiveModelTurnState,
    SlowLivePostModelReplyState,
    coerce_model_turn_state,
    coerce_post_model_reply_state,
)
from xinyu_bridge_turn_finish_sidecars import run_slow_turn_finish_sidecars


TraceRouteStage = Callable[..., Any]
FinishSidecarsRunner = Callable[..., Any]


async def run_slow_live_finish_sidecars_with_trace(
    runtime: Any,
    *,
    sidecars_runner: FinishSidecarsRunner,
    trace_route_stage: TraceRouteStage,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        trace_route_stage("finish_sidecars_started", route="slow_live")
        finish_sidecars = await sidecars_runner(runtime, **kwargs)
        trace_route_stage("finish_sidecars_finished", route="slow_live", status="ok")
        return finish_sidecars
    except TimeoutError:
        trace_route_stage(
            "finish_sidecars_timeout",
            route="slow_live",
            status="timeout",
            notes=["finish_sidecars_timeout"],
        )
        raise
    except Exception as exc:
        trace_route_stage(
            "finish_sidecars_error",
            route="slow_live",
            status="error",
            notes=[f"finish_sidecars_error:{type(exc).__name__}"],
        )
        raise


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
    finish_sidecars_with_trace_func: Callable[..., Any] | None = None,
    sidecars_runner: FinishSidecarsRunner | None = None,
    build_success_notes_func: Callable[..., list[str]] | None = None,
    publish_success_func: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    finish_sidecars_with_trace_func = finish_sidecars_with_trace_func or run_slow_live_finish_sidecars_with_trace
    sidecars_runner = sidecars_runner or run_slow_turn_finish_sidecars
    build_success_notes_func = build_success_notes_func or build_slow_live_success_notes
    publish_success_func = publish_success_func or publish_slow_live_success_turn

    finish_kwargs = dict(locals())
    finish_kwargs.pop("runtime")
    finish_kwargs.pop("payload")
    return await _finish_and_publish_slow_live_success_turn(
        runtime,
        payload,
        **finish_kwargs,
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
    finish_success_func: Callable[..., Any] | None = None,
    model_turn_coercer: Callable[..., SlowLiveModelTurnState] | None = None,
    post_model_reply_coercer: Callable[..., SlowLivePostModelReplyState] | None = None,
) -> dict[str, Any]:
    finish_success_func = finish_success_func or finish_and_publish_slow_live_success_turn
    model_turn_coercer = model_turn_coercer or coerce_model_turn_state
    post_model_reply_coercer = post_model_reply_coercer or coerce_post_model_reply_state

    prepared_kwargs = dict(locals())
    prepared_kwargs.pop("runtime")
    prepared_kwargs.pop("payload")
    return await _finish_prepared_slow_live_success_turn(
        runtime,
        payload,
        **prepared_kwargs,
    )
