from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from xinyu_bridge_slow_live_context_prompt import (
    build_slow_live_model_contexts as _build_slow_live_model_contexts,
)
from xinyu_bridge_slow_live_context_recall import (
    run_slow_live_memory_recall as _run_slow_live_memory_recall,
)
from xinyu_bridge_slow_live_context_sidecars import (
    build_slow_live_response_state as _build_slow_live_response_state,
    observe_slow_live_persona_sidecar as _observe_slow_live_persona_sidecar,
    run_slow_live_emotion_council_shadow as _run_slow_live_emotion_council_shadow,
)
from xinyu_bridge_slow_live_state import (
    SlowLiveMemoryRecallResult,
    SlowLiveModelContexts,
    SlowLiveResponseState,
)
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_continuity_handoff import refresh_continuity_handoff
from xinyu_emotion_council import build_emotion_council_prompt_block, run_emotion_council_shadow
from xinyu_living_memory_recall import run_living_memory_recall_algorithm
from xinyu_persona_state import observe_persona_turn
from xinyu_response_error_loop import classify_response_error
from xinyu_runtime_presence import build_runtime_presence_prompt_block
from xinyu_scene_frame import build_scene_frame
from xinyu_slow_state_modulator import build_slow_state


TraceRouteStage = Callable[..., Any]
MemoryRecallRunner = Callable[..., Any]


async def run_slow_live_memory_recall(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    session: Any,
    session_key: str,
    turn_id: str,
    visible_turn: Any,
    evaluated_at: str,
    trace_route_stage: TraceRouteStage,
    recall_runner: MemoryRecallRunner | None = None,
    safe_str_func: Callable[..., str] = _safe_str,
) -> SlowLiveMemoryRecallResult:
    return await _run_slow_live_memory_recall(
        runtime,
        payload,
        user_text=user_text,
        session=session,
        session_key=session_key,
        turn_id=turn_id,
        visible_turn=visible_turn,
        evaluated_at=evaluated_at,
        trace_route_stage=trace_route_stage,
        recall_runner=recall_runner or run_living_memory_recall_algorithm,
        safe_str_func=safe_str_func,
    )


async def build_slow_live_model_contexts(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    visible_turn: Any,
    recalled_context: Any,
    evaluated_at: str,
    continuity_refresher: Callable[..., dict[str, Any]] | None = None,
    runtime_presence_builder: Callable[..., str] | None = None,
    emotion_prompt_builder: Callable[..., str] | None = None,
    now_func: Callable[[], datetime] | None = None,
    safe_str_func: Callable[..., str] = _safe_str,
) -> SlowLiveModelContexts:
    return await _build_slow_live_model_contexts(
        runtime,
        payload,
        user_text=user_text,
        visible_turn=visible_turn,
        recalled_context=recalled_context,
        evaluated_at=evaluated_at,
        continuity_refresher=continuity_refresher or refresh_continuity_handoff,
        runtime_presence_builder=runtime_presence_builder or build_runtime_presence_prompt_block,
        emotion_prompt_builder=emotion_prompt_builder or build_emotion_council_prompt_block,
        now_func=now_func,
        safe_str_func=safe_str_func,
    )


def observe_slow_live_persona_sidecar(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    observer: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return _observe_slow_live_persona_sidecar(
        runtime,
        payload,
        text=text,
        observer=observer or observe_persona_turn,
    )


def run_slow_live_emotion_council_shadow(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    checked_at: str | None = None,
    runner: Callable[..., dict[str, Any]] | None = None,
    now_func: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    return _run_slow_live_emotion_council_shadow(
        runtime,
        payload,
        text=text,
        checked_at=checked_at,
        runner=runner or run_emotion_council_shadow,
        now_func=now_func,
    )


def build_slow_live_response_state(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    visible_turn: Any,
    recalled_context: Any,
    evaluated_at: str,
    response_classifier: Callable[..., Any] | None = None,
    scene_builder: Callable[..., Any] | None = None,
    slow_state_builder: Callable[..., Any] | None = None,
    safe_str_func: Callable[..., str] = _safe_str,
) -> SlowLiveResponseState:
    return _build_slow_live_response_state(
        runtime,
        payload,
        user_text=user_text,
        reply=reply,
        visible_turn=visible_turn,
        recalled_context=recalled_context,
        evaluated_at=evaluated_at,
        response_classifier=response_classifier or classify_response_error,
        scene_builder=scene_builder or build_scene_frame,
        slow_state_builder=slow_state_builder or build_slow_state,
        safe_str_func=safe_str_func,
    )
