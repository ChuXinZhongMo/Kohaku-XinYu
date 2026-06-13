from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_slow_live_reply_pipeline import (
    apply_reply_adjustment_pipeline as _apply_reply_adjustment_pipeline,
)


TraceRouteStage = Callable[..., Any]


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
    outward_renderer_func: Callable[..., Any],
    final_reply_guard_func: Callable[..., Any],
    visible_dedupe_func: Callable[..., dict[str, Any]],
    stale_context_repair_func: Callable[..., dict[str, Any]],
    life_reply_policy_func: Callable[..., dict[str, Any]],
    current_reference_repair_func: Callable[..., dict[str, Any]],
    reply_bubble_policy_func: Callable[..., dict[str, Any]],
    sticker_reply_override_func: Callable[..., dict[str, Any]],
    style_pressure_empty_fallback_func: Callable[..., dict[str, Any]],
    empty_visible_recovery_func: Callable[..., Any],
) -> dict[str, Any]:
    return await _apply_reply_adjustment_pipeline(
        runtime,
        session,
        payload,
        reply=reply,
        draft_reply=draft_reply,
        user_text=user_text,
        recalled_context=recalled_context,
        life_reply_policy=life_reply_policy,
        trace_route_stage=trace_route_stage,
        blocked_by_delegate=blocked_by_delegate,
        codex_delegate_blocked=codex_delegate_blocked,
        outward_renderer_func=outward_renderer_func,
        final_reply_guard_func=final_reply_guard_func,
        visible_dedupe_func=visible_dedupe_func,
        stale_context_repair_func=stale_context_repair_func,
        life_reply_policy_func=life_reply_policy_func,
        current_reference_repair_func=current_reference_repair_func,
        reply_bubble_policy_func=reply_bubble_policy_func,
        sticker_reply_override_func=sticker_reply_override_func,
        style_pressure_empty_fallback_func=style_pressure_empty_fallback_func,
        empty_visible_recovery_func=empty_visible_recovery_func,
    )
