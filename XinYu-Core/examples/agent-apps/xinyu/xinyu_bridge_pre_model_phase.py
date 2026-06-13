from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_pre_model_state import PreModelPhaseState


TraceRouteStage = Callable[..., Any]


async def run_pre_model_phase_with_trace(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    cleanup: dict[str, Any],
    desktop_started_published: bool,
    timeout_seconds: float,
    trace_route_stage: TraceRouteStage,
    publish_started_func: Callable[..., Any],
    memory_snapshot_func: Callable[..., dict[str, Any]],
    observations_func: Callable[..., dict[str, dict[str, Any]]],
    routes_with_timeout_func: Callable[..., Any],
    route_runner_func: Callable[..., Any],
    safe_str_func: Callable[..., str],
) -> PreModelPhaseState:
    if not desktop_started_published:
        desktop_started_published = await publish_started_func(
            runtime,
            payload,
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            active_sessions=len(runtime._sessions),
            trace_route_stage=trace_route_stage,
        )
    before_memory = memory_snapshot_func(runtime, trace_route_stage=trace_route_stage)
    observations = observations_func(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        trace_route_stage=trace_route_stage,
    )
    pre_model_routes = await routes_with_timeout_func(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        timeout_seconds=timeout_seconds,
        trace_route_stage=trace_route_stage,
        runner=route_runner_func,
    )
    if pre_model_routes.response is not None:
        pre_model_notes = pre_model_routes.response.get("notes", [])
        if not isinstance(pre_model_notes, list):
            pre_model_notes = []
        trace_route_stage(
            "route_finished",
            route="pre_model",
            status="ok",
            notes=[safe_str_func(note) for note in pre_model_notes[:8]],
        )
    return PreModelPhaseState(
        response=pre_model_routes.response,
        desktop_started_published=desktop_started_published,
        before_memory=before_memory,
        curiosity_eval=observations["curiosity_eval"],
        private_thought_outcome=observations["private_thought_outcome"],
        uncertainty_pause_reply=observations["uncertainty_pause_reply"],
        event_sidecar=pre_model_routes.event_sidecar,
        v1_shadow=pre_model_routes.v1_shadow,
        tinykernel_shadow=pre_model_routes.tinykernel_shadow,
    )
