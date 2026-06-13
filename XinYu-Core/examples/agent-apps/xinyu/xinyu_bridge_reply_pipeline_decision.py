from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable


TraceRouteStage = Callable[..., Any]
RenderOutwardReply = Callable[..., Awaitable[str]]


async def render_outward_reply_with_trace_impl(
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


def runtime_speech_controller_impl(
    runtime: Any,
    *,
    bridge_source_path: Path,
    controller_cls: Callable[[Path], Any],
) -> Any:
    controller = getattr(runtime, "speech_controller", None)
    if controller is None:
        controller = controller_cls(Path(bridge_source_path).parent)
        runtime.speech_controller = controller
    return controller


def runtime_is_live_style_pressure_impl(runtime: Any, text: str) -> bool:
    return runtime._speech_controller().is_live_style_pressure(text)


def runtime_is_owner_relationship_pressure_impl(runtime: Any, text: str) -> bool:
    return runtime._speech_controller().is_owner_relationship_pressure(text)


def runtime_is_explicit_technical_request_impl(runtime: Any, text: str) -> bool:
    return runtime._speech_controller().is_explicit_technical_request(text)


def runtime_reply_quality_flags_impl(runtime: Any, *, user_text: str, reply: str) -> list[str]:
    return runtime._speech_controller().reply_quality_flags(user_text=user_text, reply=reply)
