from __future__ import annotations

from typing import Any, Awaitable, Callable

from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_visible_reply_guard import dedupe_visible_reply


TraceRouteStage = Callable[..., Any]
RenderOutwardReply = Callable[..., Awaitable[str]]


async def render_outward_reply_with_trace(
    render_outward_reply: RenderOutwardReply,
    agent: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    draft_reply: str,
    canonical_recall_context: str = "",
    reason: str,
    trace_route_stage: TraceRouteStage,
) -> str:
    try:
        trace_route_stage(
            "outward_renderer_started",
            route="slow_live",
            notes=[f"reason:{reason}"],
        )
        rendered_reply = await render_outward_reply(
            agent,
            payload=payload,
            user_text=user_text,
            draft_reply=draft_reply,
            canonical_recall_context=canonical_recall_context,
        )
        trace_route_stage(
            "outward_renderer_finished",
            route="slow_live",
            status="ok",
            notes=[f"reason:{reason}"],
        )
        return rendered_reply
    except TimeoutError:
        trace_route_stage(
            "outward_renderer_timeout",
            route="slow_live",
            status="timeout",
            notes=[f"reason:{reason}"],
        )
        raise
    except Exception as exc:
        trace_route_stage(
            "outward_renderer_error",
            route="slow_live",
            status="error",
            notes=[f"reason:{reason}", f"renderer_error:{type(exc).__name__}"],
        )
        raise


async def recover_empty_visible_reply(
    runtime: Any,
    agent: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    canonical_recall_context: str = "",
) -> tuple[str, list[str]]:
    if not runtime._owner_private_payload_matches(payload):
        return "", []
    try:
        rendered = await runtime._render_outward_reply(
            agent,
            payload=payload,
            user_text=user_text,
            draft_reply="",
            canonical_recall_context=canonical_recall_context,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] empty visible reply recovery failed: {type(exc).__name__}: {exc}", flush=True)
        return "", ["empty_visible_reply_retry_error"]

    recovered = normalize_bridge_reply(rendered)
    if not recovered:
        return "", ["empty_visible_reply_retry_empty"]

    guarded, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=user_text,
        reply=recovered,
    )
    if not guarded:
        return "", _dedupe(["empty_visible_reply_retry_blocked"] + guard_flags)

    visible_dedupe = dedupe_visible_reply(guarded)
    return visible_dedupe.text, _dedupe(
        ["empty_visible_reply_regenerated"] + list(guard_flags) + list(visible_dedupe.notes)
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
