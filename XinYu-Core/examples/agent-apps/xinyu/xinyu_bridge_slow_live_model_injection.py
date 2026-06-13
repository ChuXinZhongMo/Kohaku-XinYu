from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from xinyu_bridge_slow_live_model_context import (
    inject_slow_live_turn_context as _inject_slow_live_turn_context,
    start_early_visible_shadow as _start_early_visible_shadow,
    stop_early_visible_shadow as _stop_early_visible_shadow,
)
from xinyu_bridge_slow_live_model_payload import (
    has_visible_chunks,
    int_or_zero,
    owner_private_payload_matches,
    session_output_notes,
)
from xinyu_bridge_slow_live_model_retry import (
    EMPTY_VISIBLE_RETRY_TIMEOUT_SECONDS,
    create_empty_visible_retry_event,
    retry_empty_visible_owner_private_output as _retry_empty_visible_owner_private_output,
)
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_continuity_handoff import build_continuity_handoff_prompt_block
from xinyu_early_visible_segment import observe_early_visible_segment_shadow
from xinyu_life_reply_policy import build_life_reply_prompt_block
from xinyu_uncertainty_pause import build_uncertainty_pause_prompt_block


TraceRouteStage = Callable[..., Any]


async def inject_slow_live_model_event(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session: Any,
    event: Any,
    text: str,
    turn_id: str,
    visible_turn: Any,
    persona_sidecar: dict[str, Any],
    curiosity_eval: dict[str, Any],
    recalled_context: Any,
    runtime_presence_context: str,
    life_reply_policy: dict[str, Any],
    emotion_council_context: str,
    trace_route_stage: TraceRouteStage,
    safe_str_func: Callable[..., str] = _safe_str,
    int_or_zero_func: Callable[[Any], int] = int_or_zero,
    session_output_notes_func: Callable[..., list[str]] = session_output_notes,
    has_visible_chunks_func: Callable[..., bool] = has_visible_chunks,
    owner_private_payload_matches_func: Callable[..., bool] = owner_private_payload_matches,
    create_retry_event_func: Callable[..., Any] = create_empty_visible_retry_event,
    build_continuity_func: Callable[..., str] = build_continuity_handoff_prompt_block,
    build_uncertainty_func: Callable[..., str] = build_uncertainty_pause_prompt_block,
    build_life_reply_func: Callable[..., str] = build_life_reply_prompt_block,
    observe_early_visible_func: Callable[..., Any] = observe_early_visible_segment_shadow,
    empty_visible_retry_timeout_seconds: int = EMPTY_VISIBLE_RETRY_TIMEOUT_SECONDS,
    create_task_func: Callable[..., asyncio.Task[Any]] = asyncio.create_task,
    wait_for_func: Callable[..., Any] = asyncio.wait_for,
    get_running_loop_func: Callable[[], asyncio.AbstractEventLoop] = asyncio.get_running_loop,
) -> None:
    stop_early_shadow, early_shadow_task = _start_early_visible_shadow(
        runtime,
        payload,
        session=session,
        text=text,
        turn_id=turn_id,
        visible_turn=visible_turn,
        safe_str_func=safe_str_func,
        observe_early_visible_func=observe_early_visible_func,
        create_task_func=create_task_func,
        get_running_loop_func=get_running_loop_func,
    )
    try:
        trace_route_stage("model_inject_started", route="slow_live")
        _inject_slow_live_turn_context(
            runtime,
            payload=payload,
            session=session,
            text=text,
            turn_id=turn_id,
            visible_turn=visible_turn,
            persona_sidecar=persona_sidecar,
            curiosity_eval=curiosity_eval,
            recalled_context=recalled_context,
            runtime_presence_context=runtime_presence_context,
            life_reply_policy=life_reply_policy,
            emotion_council_context=emotion_council_context,
            safe_str_func=safe_str_func,
            build_continuity_func=build_continuity_func,
            build_uncertainty_func=build_uncertainty_func,
            build_life_reply_func=build_life_reply_func,
        )
        await wait_for_func(
            session.agent.inject_event(event),
            timeout=runtime.turn_timeout_seconds,
        )
        output_notes = session_output_notes_func(session)
        output_notes = await _retry_empty_visible_owner_private_output(
            runtime,
            payload,
            session=session,
            text=text,
            turn_id=turn_id,
            output_notes=output_notes,
            trace_route_stage=trace_route_stage,
            safe_str_func=safe_str_func,
            int_or_zero_func=int_or_zero_func,
            session_output_notes_func=session_output_notes_func,
            has_visible_chunks_func=has_visible_chunks_func,
            owner_private_payload_matches_func=owner_private_payload_matches_func,
            create_retry_event_func=create_retry_event_func,
            empty_visible_retry_timeout_seconds=empty_visible_retry_timeout_seconds,
            wait_for_func=wait_for_func,
        )
        trace_route_stage(
            "model_inject_finished",
            route="slow_live",
            status="ok",
            notes=output_notes,
        )
    except TimeoutError:
        trace_route_stage(
            "model_inject_timeout",
            route="slow_live",
            status="timeout",
            notes=["turn_timeout"],
        )
        raise
    except Exception as exc:
        trace_route_stage(
            "model_inject_error",
            route="slow_live",
            status="error",
            notes=[f"turn_error:{type(exc).__name__}"],
        )
        raise
    finally:
        await _stop_early_visible_shadow(
            stop_early_shadow,
            early_shadow_task,
            wait_for_func=wait_for_func,
        )
