from __future__ import annotations

from typing import Any

from xinyu_bridge_semantic_fast_pipeline import (
    probe_semantic_fast_decision_with_trace as _runtime_probe_semantic_fast_decision_with_trace,
    try_initial_semantic_fast_route_with_trace as _runtime_try_initial_semantic_fast_route_with_trace,
    try_pre_slow_semantic_fast_route_with_trace as _runtime_try_pre_slow_semantic_fast_route_with_trace,
)


def probe_semantic_fast_decision_with_trace(
    hooks: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    trace_route_stage: Any,
) -> dict[str, Any]:
    return _runtime_probe_semantic_fast_decision_with_trace(
        runtime,
        payload,
        text=text,
        trace_route_stage=trace_route_stage,
        safe_str_func=hooks._safe_str,
    )


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
    trace_route_stage: Any,
) -> dict[str, Any] | None:
    return await _runtime_try_pre_slow_semantic_fast_route_with_trace(
        runtime,
        payload,
        text=text,
        session=session,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
        trace_route_stage=trace_route_stage,
    )


async def try_initial_semantic_fast_route_with_trace(
    hooks: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    cleanup: dict[str, Any],
    trace_route_stage: Any,
) -> Any:
    return await _runtime_try_initial_semantic_fast_route_with_trace(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        cleanup=cleanup,
        trace_route_stage=trace_route_stage,
        probe_func=hooks.probe_semantic_fast_decision_with_trace,
        publish_started_func=hooks.publish_chat_started_with_trace,
        safe_str_func=hooks._safe_str,
    )
