from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

from xinyu_environment_sensor import sample_environment
from xinyu_experience_frame import read_recent_action_context
from xinyu_life_kernel import build_entropy_state
from xinyu_life_reply_policy import build_life_reply_policy
from xinyu_bridge_reply_pipeline_decision import (
    render_outward_reply_with_trace_impl,
    runtime_is_explicit_technical_request_impl,
    runtime_is_live_style_pressure_impl,
    runtime_is_owner_relationship_pressure_impl,
    runtime_reply_quality_flags_impl,
    runtime_speech_controller_impl,
)
from xinyu_bridge_reply_pipeline_normalization import (
    dedupe_preserving_order,
    recover_empty_visible_reply_impl,
)
from xinyu_bridge_reply_pipeline_payload import runtime_render_outward_reply_impl
from xinyu_bridge_reply_policy_runtime import build_life_reply_policy_for_runtime_impl
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_scene_frame import build_scene_frame
from xinyu_speech_controller import XinyuSpeechController
from xinyu_visible_reply_guard import dedupe_visible_reply


TraceRouteStage = Callable[..., Any]
RenderOutwardReply = Callable[..., Awaitable[str]]


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
