from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

from xinyu_environment_sensor import sample_environment
from xinyu_experience_frame import read_recent_action_context
from xinyu_life_kernel import build_entropy_state
from xinyu_life_reply_policy import build_life_reply_policy
from xinyu_bridge_reply_policy_runtime import build_life_reply_policy_for_runtime_impl
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_scene_frame import build_scene_frame
from xinyu_speech_controller import XinyuSpeechController
from xinyu_visible_reply_guard import dedupe_visible_reply


TraceRouteStage = Callable[..., Any]
RenderOutwardReply = Callable[..., Awaitable[str]]
NormalizeBridgeReply = Callable[[str], str]
DedupeNotes = Callable[[list[str]], list[str]]
DedupeVisibleReply = Callable[[str], Any]


# ---------------------------------------------------------------------------
# Implementation helpers. Consolidated 2026-06-15 from the former
# xinyu_bridge_reply_pipeline_{payload,decision,normalization}.py modules, which
# were imported only by this file. Behaviour is unchanged.
# ---------------------------------------------------------------------------


async def runtime_render_outward_reply_impl(
    runtime: Any,
    agent: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    draft_reply: str,
    canonical_recall_context: str = "",
) -> str:
    return await runtime.renderer.render_outward_reply(
        agent,
        payload=payload,
        user_text=user_text,
        draft_reply=draft_reply,
        canonical_recall_context=canonical_recall_context,
    )


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


async def recover_empty_visible_reply_impl(
    runtime: Any,
    agent: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    canonical_recall_context: str = "",
    normalize_reply_func: NormalizeBridgeReply,
    dedupe_visible_reply_func: DedupeVisibleReply,
    dedupe_notes_func: DedupeNotes,
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

    recovered = normalize_reply_func(rendered)
    if not recovered:
        return "", ["empty_visible_reply_retry_empty"]

    guarded, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=user_text,
        reply=recovered,
    )
    guard_flags = list(guard_flags)
    if not guarded:
        return "", dedupe_notes_func(["empty_visible_reply_retry_blocked"] + guard_flags)

    visible_dedupe = dedupe_visible_reply_func(guarded)
    return visible_dedupe.text, dedupe_notes_func(
        ["empty_visible_reply_regenerated"] + guard_flags + list(visible_dedupe.notes)
    )


def dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


# ---------------------------------------------------------------------------
# Public facade (runtime-bound entry points; unchanged).
# ---------------------------------------------------------------------------


async def runtime_render_outward_reply(
    runtime: Any,
    agent: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    draft_reply: str,
    canonical_recall_context: str = "",
) -> str:
    return await runtime_render_outward_reply_impl(
        runtime,
        agent,
        payload=payload,
        user_text=user_text,
        draft_reply=draft_reply,
        canonical_recall_context=canonical_recall_context,
    )


async def build_life_reply_policy_for_runtime(
    runtime: Any,
    *,
    user_text: str,
    visible_turn: Any | None = None,
    canonical_recall_context: str = "",
    evaluated_at: Any | None = None,
) -> dict[str, Any]:
    return await build_life_reply_policy_for_runtime_impl(
        runtime,
        user_text=user_text,
        visible_turn=visible_turn,
        canonical_recall_context=canonical_recall_context,
        evaluated_at=evaluated_at,
        sample_environment_func=sample_environment,
        build_entropy_state_func=build_entropy_state,
        build_scene_frame_func=build_scene_frame,
        read_recent_action_context_func=read_recent_action_context,
        build_life_reply_policy_func=build_life_reply_policy,
    )


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
    return await render_outward_reply_with_trace_impl(
        render_outward_reply,
        agent,
        payload=payload,
        user_text=user_text,
        draft_reply=draft_reply,
        canonical_recall_context=canonical_recall_context,
        reason=reason,
        trace_route_stage=trace_route_stage,
    )


async def recover_empty_visible_reply(
    runtime: Any,
    agent: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    canonical_recall_context: str = "",
) -> tuple[str, list[str]]:
    return await recover_empty_visible_reply_impl(
        runtime,
        agent,
        payload=payload,
        user_text=user_text,
        canonical_recall_context=canonical_recall_context,
        normalize_reply_func=normalize_bridge_reply,
        dedupe_visible_reply_func=dedupe_visible_reply,
        dedupe_notes_func=_dedupe,
    )


def _dedupe(values: list[str]) -> list[str]:
    return dedupe_preserving_order(values)


def runtime_speech_controller(runtime: Any, *, bridge_source_path: Path) -> XinyuSpeechController:
    return runtime_speech_controller_impl(
        runtime,
        bridge_source_path=bridge_source_path,
        controller_cls=XinyuSpeechController,
    )


def runtime_is_live_style_pressure(runtime: Any, text: str) -> bool:
    return runtime_is_live_style_pressure_impl(runtime, text)


def runtime_is_owner_relationship_pressure(runtime: Any, text: str) -> bool:
    return runtime_is_owner_relationship_pressure_impl(runtime, text)


def runtime_is_explicit_technical_request(runtime: Any, text: str) -> bool:
    return runtime_is_explicit_technical_request_impl(runtime, text)


def runtime_reply_quality_flags(runtime: Any, *, user_text: str, reply: str) -> list[str]:
    return runtime_reply_quality_flags_impl(runtime, user_text=user_text, reply=reply)
