from __future__ import annotations

from typing import Any

from xinyu_bridge_semantic_fast_pipeline_stage import SEMANTIC_FAST_ROUTE, TraceRouteStage


def deferred_semantic_fast_event_sidecar() -> dict[str, list[str]]:
    return {"notes": ["event_sourcing_deferred_for_semantic_fast"]}


def semantic_fast_publish_started_kwargs(
    runtime: Any,
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    trace_route_stage: TraceRouteStage,
) -> dict[str, Any]:
    return {
        "text": text,
        "session_key": session_key,
        "turn_id": turn_id,
        "turn_started_wall": turn_started_wall,
        "active_sessions": len(runtime._sessions),
        "trace_route_stage": trace_route_stage,
        "route": SEMANTIC_FAST_ROUTE,
    }


def pre_slow_semantic_fast_turn_kwargs(
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
) -> dict[str, Any]:
    return {
        "text": text,
        "session": session,
        "session_key": session_key,
        "turn_id": turn_id,
        "turn_started_wall": turn_started_wall,
        "turn_started_at": turn_started_at,
        "before_memory": before_memory,
        "cleanup": cleanup,
        "event_sidecar": event_sidecar,
    }


def initial_semantic_fast_turn_kwargs(
    *,
    text: str,
    session: Any,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    cleanup: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    return {
        "text": text,
        "session": session,
        "session_key": session_key,
        "turn_id": turn_id,
        "turn_started_wall": turn_started_wall,
        "turn_started_at": turn_started_at,
        "before_memory": None,
        "cleanup": cleanup,
        "event_sidecar": deferred_semantic_fast_event_sidecar(),
        "decision": decision,
        "record_decision_stage": False,
    }
