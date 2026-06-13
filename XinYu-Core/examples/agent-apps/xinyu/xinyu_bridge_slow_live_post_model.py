from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_bridge_slow_live_state import SlowLiveModelTurnState, SlowLivePostModelReplyState


TraceRouteStage = Callable[..., Any]


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
    clock_func: Callable[[], float],
    codex_delegate_func: Callable[..., Any],
    reply_adjustment_pipeline_func: Callable[..., Any],
    response_state_builder_func: Callable[..., Any],
    normalize_func: Callable[[str], str] = normalize_bridge_reply,
) -> SlowLivePostModelReplyState:
    session.last_used_at = clock_func()
    draft_reply = normalize_func("".join(session.chunks))
    model_codex_task = runtime._extract_model_codex_delegate(draft_reply)
    wait_to_think_task = runtime._extract_wait_to_think_task(
        draft_reply,
        user_text=text,
        session_key=session_key,
    )
    self_code_task = runtime._owner_self_code_iteration_task(
        payload,
        user_text=text,
        reply=draft_reply,
        session_key=session_key,
    )
    codex_reply = await codex_delegate_func(
        runtime,
        session,
        payload,
        user_text=text,
        draft_reply=draft_reply,
        session_key=session_key,
        self_code_task=self_code_task,
        model_codex_task=model_codex_task,
        wait_to_think_task=wait_to_think_task,
    )
    reply = codex_reply["reply"]
    direct_codex_task = codex_reply["direct_codex_task"]
    wait_to_think_sidecar = codex_reply["wait_to_think_sidecar"]
    model_codex_delegate_note = codex_reply["model_codex_delegate_note"]
    reply_adjustment_blocked = bool(self_code_task or model_codex_task or direct_codex_task or wait_to_think_task)
    reply_adjustment = await reply_adjustment_pipeline_func(
        runtime,
        session,
        payload,
        reply=reply,
        draft_reply=draft_reply,
        user_text=text,
        recalled_context=recalled_context,
        life_reply_policy=life_reply_policy,
        trace_route_stage=trace_route_stage,
        blocked_by_delegate=reply_adjustment_blocked,
        codex_delegate_blocked=bool(self_code_task or model_codex_task or direct_codex_task),
    )
    response_state = response_state_builder_func(
        runtime,
        payload,
        user_text=text,
        reply=reply_adjustment["reply"],
        visible_turn=visible_turn,
        recalled_context=recalled_context,
        evaluated_at=evaluated_at,
    )
    return SlowLivePostModelReplyState(
        draft_reply=draft_reply,
        reply=reply_adjustment["reply"],
        self_code_task=self_code_task,
        direct_codex_task=direct_codex_task,
        model_codex_task=model_codex_task,
        wait_to_think_task=wait_to_think_task,
        model_codex_delegate_note=model_codex_delegate_note,
        wait_to_think_sidecar=wait_to_think_sidecar,
        rendered=reply_adjustment["rendered"],
        renderer_reason=reply_adjustment["renderer_reason"],
        final_guard_flags=reply_adjustment["final_guard_flags"],
        final_guard_applied=reply_adjustment["final_guard_applied"],
        expression_learning=reply_adjustment["expression_learning"],
        visible_dedupe=reply_adjustment["visible_dedupe"],
        stale_context_reply_replaced=reply_adjustment["stale_context_reply_replaced"],
        life_reply_adjustment=reply_adjustment["life_reply_adjustment"],
        current_sticker_reply=reply_adjustment["current_sticker_reply"],
        recent_sticker_reply=reply_adjustment["recent_sticker_reply"],
        reply_bubble_force_units=reply_adjustment["reply_bubble_force_units"],
        empty_visible_reply_no_fallback=reply_adjustment["empty_visible_reply_no_fallback"],
        response_error_loop=response_state["response_error_loop"],
        slow_state_runtime=response_state["slow_state_runtime"],
    )


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
    prepare_func: Callable[..., Any],
) -> SlowLivePostModelReplyState:
    return await prepare_func(
        runtime,
        session,
        payload,
        text=text,
        session_key=session_key,
        recalled_context=model_turn["recalled_context"],
        life_reply_policy=model_turn["life_reply_policy"],
        visible_turn=model_turn["visible_turn"],
        evaluated_at=evaluated_at,
        trace_route_stage=trace_route_stage,
    )
