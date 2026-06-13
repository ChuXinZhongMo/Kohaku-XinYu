from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_reply_pipeline import render_outward_reply_with_trace
from xinyu_bridge_slow_live_reply_rendering import (
    apply_final_reply_guard as _apply_final_reply_guard,
)
from xinyu_bridge_slow_live_reply_rendering import apply_outward_renderer as _apply_outward_renderer
from xinyu_bridge_values import dedupe as _dedupe
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_expression_self_learning import record_expression_self_learning_event


TraceRouteStage = Callable[..., Any]


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
    render_func: Callable[..., Any] = render_outward_reply_with_trace,
    expression_record_func: Callable[..., dict[str, Any]] = record_expression_self_learning_event,
    safe_str_func: Callable[..., str] = _safe_str,
    dedupe_func: Callable[[list[str]], list[str]] = _dedupe,
) -> dict[str, Any]:
    return await _apply_final_reply_guard(
        runtime,
        session,
        payload,
        reply=reply,
        user_text=user_text,
        recalled_context=recalled_context,
        trace_route_stage=trace_route_stage,
        codex_delegate_blocked=codex_delegate_blocked,
        render_func=render_func,
        expression_record_func=expression_record_func,
        safe_str_func=safe_str_func,
        dedupe_func=dedupe_func,
    )


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
    render_func: Callable[..., Any] = render_outward_reply_with_trace,
    safe_str_func: Callable[..., str] = _safe_str,
) -> dict[str, Any]:
    return await _apply_outward_renderer(
        runtime,
        session,
        payload,
        reply=reply,
        draft_reply=draft_reply,
        user_text=user_text,
        recalled_context=recalled_context,
        trace_route_stage=trace_route_stage,
        blocked_by_delegate=blocked_by_delegate,
        render_func=render_func,
        safe_str_func=safe_str_func,
    )
