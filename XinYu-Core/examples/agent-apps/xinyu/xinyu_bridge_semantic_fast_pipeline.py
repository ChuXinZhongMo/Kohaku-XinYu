from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_pre_model_state import InitialSemanticFastState
from xinyu_bridge_semantic_fast_pipeline_payload import (
    initial_semantic_fast_turn_kwargs,
    pre_slow_semantic_fast_turn_kwargs,
    semantic_fast_publish_started_kwargs,
)
from xinyu_bridge_semantic_fast_pipeline_result import (
    exception_note,
    initial_semantic_fast_state,
    probe_error_decision,
)
from xinyu_bridge_semantic_fast_pipeline_stage import (
    TraceRouteStage,
    trace_semantic_fast_direct_finished_empty,
    trace_semantic_fast_direct_started,
    trace_semantic_fast_fell_through_empty,
    trace_semantic_fast_fell_through_error,
    trace_semantic_fast_probe_error,
    trace_semantic_fast_probe_finished,
    trace_semantic_fast_probe_started,
    trace_semantic_fast_route_decided,
    trace_semantic_fast_session_finished,
    trace_semantic_fast_session_started,
    trace_slow_live_route_after_semantic_fast,
)
from xinyu_bridge_values import safe_str


def probe_semantic_fast_decision_with_trace(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    trace_route_stage: TraceRouteStage,
    safe_str_func: Callable[..., str] = safe_str,
) -> dict[str, Any]:
    try:
        trace_semantic_fast_probe_started(trace_route_stage)
        decision = runtime._owner_private_semantic_fast_decision(payload, text)
        trace_semantic_fast_probe_finished(trace_route_stage, decision, safe_str_func=safe_str_func)
        return decision
    except Exception as exc:
        print(f"[xinyu_core_bridge] semantic fast probe failed: {type(exc).__name__}: {exc}", flush=True)
        decision = probe_error_decision(exc)
        trace_semantic_fast_probe_error(trace_route_stage, decision["notes"][0])
        return decision


async def try_pre_slow_semantic_fast_route_with_trace(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session: Any,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
    trace_route_stage: TraceRouteStage,
) -> dict[str, Any] | None:
    response = await runtime._maybe_handle_owner_private_semantic_fast_turn(
        payload,
        **pre_slow_semantic_fast_turn_kwargs(
            text=text,
            session=session,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            before_memory=before_memory,
            cleanup=cleanup,
            event_sidecar=event_sidecar,
        ),
    )
    if response is not None:
        return response
    trace_slow_live_route_after_semantic_fast(trace_route_stage)
    return None


async def try_initial_semantic_fast_route_with_trace(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    cleanup: dict[str, Any],
    trace_route_stage: TraceRouteStage,
    probe_func: Callable[..., dict[str, Any]],
    publish_started_func: Callable[..., Any],
    safe_str_func: Callable[..., str] = safe_str,
) -> InitialSemanticFastState:
    decision = probe_func(
        runtime,
        payload,
        text=text,
        trace_route_stage=trace_route_stage,
    )
    desktop_started_published = False
    if not decision.get("allowed"):
        return initial_semantic_fast_state(
            response=None,
            desktop_started_published=desktop_started_published,
            decision=decision,
        )

    trace_semantic_fast_route_decided(trace_route_stage, decision, safe_str_func=safe_str_func)
    desktop_started_published = await publish_started_func(
        runtime,
        payload,
        **semantic_fast_publish_started_kwargs(
            runtime,
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            trace_route_stage=trace_route_stage,
        ),
    )
    try:
        if decision.get("direct_reply"):
            trace_semantic_fast_direct_started(trace_route_stage)
            response = await runtime._maybe_handle_owner_private_semantic_fast_turn(
                payload,
                **initial_semantic_fast_turn_kwargs(
                    text=text,
                    session=None,
                    session_key=session_key,
                    turn_id=turn_id,
                    turn_started_wall=turn_started_wall,
                    turn_started_at=turn_started_at,
                    cleanup=cleanup,
                    decision=decision,
                ),
            )
            if response is not None:
                return initial_semantic_fast_state(
                    response=response,
                    desktop_started_published=desktop_started_published,
                    decision=decision,
                )
            trace_semantic_fast_direct_finished_empty(trace_route_stage)

        trace_semantic_fast_session_started(trace_route_stage)
        session = await runtime._get_session(session_key)
        trace_semantic_fast_session_finished(trace_route_stage)
        runtime._sync_recent_proactive_to_dialogue_tail(session, payload)
        response = await runtime._maybe_handle_owner_private_semantic_fast_turn(
            payload,
            **initial_semantic_fast_turn_kwargs(
                text=text,
                session=session,
                session_key=session_key,
                turn_id=turn_id,
                turn_started_wall=turn_started_wall,
                turn_started_at=turn_started_at,
                cleanup=cleanup,
                decision=decision,
            ),
        )
        if response is not None:
            return initial_semantic_fast_state(
                response=response,
                desktop_started_published=desktop_started_published,
                decision=decision,
            )
        trace_semantic_fast_fell_through_empty(trace_route_stage)
    except Exception as exc:
        print(f"[xinyu_core_bridge] semantic fast route failed: {type(exc).__name__}: {exc}", flush=True)
        trace_semantic_fast_fell_through_error(trace_route_stage, exception_note("semantic_fast_error", exc))
    return initial_semantic_fast_state(
        response=None,
        desktop_started_published=desktop_started_published,
        decision=decision,
    )
