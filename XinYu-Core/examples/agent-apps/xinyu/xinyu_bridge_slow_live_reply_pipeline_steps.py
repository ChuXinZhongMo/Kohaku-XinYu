from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from xinyu_bridge_slow_live_reply_pipeline_payload import ReplyPipelinePayload
from xinyu_bridge_slow_live_reply_pipeline_result import ReplyPipelineState


@dataclass(slots=True)
class ReplyPipelineSteps:
    outward_renderer: Callable[..., Any]
    final_reply_guard: Callable[..., Any]
    visible_dedupe: Callable[..., dict[str, Any]]
    stale_context_repair: Callable[..., dict[str, Any]]
    life_reply_policy: Callable[..., dict[str, Any]]
    current_reference_repair: Callable[..., dict[str, Any]]
    reply_bubble_policy: Callable[..., dict[str, Any]]
    sticker_reply_override: Callable[..., dict[str, Any]]
    style_pressure_empty_fallback: Callable[..., dict[str, Any]]
    empty_visible_recovery: Callable[..., Any]


async def run_reply_pipeline_steps(
    request: ReplyPipelinePayload,
    steps: ReplyPipelineSteps,
) -> ReplyPipelineState:
    state = ReplyPipelineState(reply=request.reply)

    outward_render = await steps.outward_renderer(
        request.runtime,
        request.session,
        request.payload,
        reply=state.reply,
        draft_reply=request.draft_reply,
        user_text=request.user_text,
        recalled_context=request.recalled_context,
        trace_route_stage=request.trace_route_stage,
        blocked_by_delegate=request.blocked_by_delegate,
    )
    state.reply = outward_render["reply"]
    state.rendered = outward_render["rendered"]
    state.renderer_reason = outward_render["renderer_reason"]

    final_guard_result = await steps.final_reply_guard(
        request.runtime,
        request.session,
        request.payload,
        reply=state.reply,
        user_text=request.user_text,
        recalled_context=request.recalled_context,
        trace_route_stage=request.trace_route_stage,
        codex_delegate_blocked=request.codex_delegate_blocked,
    )
    state.reply = final_guard_result["reply"]
    state.final_guard_flags = final_guard_result["final_guard_flags"]
    state.final_guard_applied = final_guard_result["final_guard_applied"]
    state.expression_learning = final_guard_result["expression_learning"]

    dedupe_result = steps.visible_dedupe(request.runtime, request.session, state.reply)
    state.reply = dedupe_result["reply"]
    state.visible_dedupe = dedupe_result["visible_dedupe"]

    stale_context_repair = steps.stale_context_repair(
        request.runtime,
        request.session,
        request.payload,
        reply=state.reply,
        user_text=request.user_text,
        final_guard_flags=state.final_guard_flags,
        blocked_by_delegate=request.blocked_by_delegate,
    )
    state.reply = stale_context_repair["reply"]
    state.final_guard_flags = stale_context_repair["final_guard_flags"]
    state.stale_context_reply_replaced = stale_context_repair["stale_context_reply_replaced"]

    life_reply_result = steps.life_reply_policy(
        request.runtime,
        request.session,
        reply=state.reply,
        user_text=request.user_text,
        life_reply_policy=request.life_reply_policy,
        blocked_by_delegate=request.blocked_by_delegate,
    )
    state.reply = life_reply_result["reply"]
    state.life_reply_adjustment = life_reply_result["life_reply_adjustment"]

    current_reference_result = steps.current_reference_repair(
        request.runtime,
        request.session,
        request.payload,
        reply=state.reply,
        user_text=request.user_text,
        final_guard_flags=state.final_guard_flags,
        blocked_by_delegate=request.blocked_by_delegate,
    )
    state.reply = current_reference_result["reply"]
    state.final_guard_flags = current_reference_result["final_guard_flags"]

    reply_bubble_result = steps.reply_bubble_policy(
        request.runtime,
        request.session,
        reply=state.reply,
        user_text=request.user_text,
        dialogue_tail=request.session.dialogue_tail,
        final_guard_flags=state.final_guard_flags,
    )
    state.reply = reply_bubble_result["reply"]
    state.final_guard_flags = reply_bubble_result["final_guard_flags"]
    state.reply_bubble_force_units = reply_bubble_result["reply_bubble_force_units"]

    sticker_reply_result = steps.sticker_reply_override(
        request.runtime,
        request.session,
        request.payload,
        reply=state.reply,
        user_text=request.user_text,
    )
    state.reply = sticker_reply_result["reply"]
    state.current_sticker_reply = sticker_reply_result["current_sticker_reply"]
    state.recent_sticker_reply = sticker_reply_result["recent_sticker_reply"]

    style_pressure_fallback = steps.style_pressure_empty_fallback(
        request.runtime,
        request.session,
        reply=state.reply,
        final_guard_flags=state.final_guard_flags,
    )
    state.reply = style_pressure_fallback["reply"]
    state.final_guard_flags = style_pressure_fallback["final_guard_flags"]

    empty_visible_recovery = await steps.empty_visible_recovery(
        request.runtime,
        request.session,
        request.payload,
        reply=state.reply,
        user_text=request.user_text,
        final_guard_flags=state.final_guard_flags,
        rendered=state.rendered,
        renderer_reason=state.renderer_reason,
        recalled_context=request.recalled_context,
        blocked_by_delegate=request.blocked_by_delegate,
    )
    state.reply = empty_visible_recovery["reply"]
    state.rendered = empty_visible_recovery["rendered"]
    state.renderer_reason = empty_visible_recovery["renderer_reason"]
    state.final_guard_flags = empty_visible_recovery["final_guard_flags"]
    state.empty_visible_reply_no_fallback = empty_visible_recovery["empty_visible_reply_no_fallback"]
    return state
