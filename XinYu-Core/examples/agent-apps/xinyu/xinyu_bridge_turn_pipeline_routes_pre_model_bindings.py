from __future__ import annotations

from typing import Any

from xinyu_bridge_turn_pipeline_routes_dispatch import (
    dispatch_pre_model_observation_sidecars_with_trace,
    dispatch_pre_model_phase_with_trace,
    dispatch_pre_model_routes,
    dispatch_pre_model_routes_with_timeout,
)
from xinyu_bridge_turn_pipeline_routes_payload import (
    build_observation_deps,
    build_observation_payload,
    build_pre_model_phase_deps,
    build_pre_model_phase_payload,
    build_routes_dispatch_deps,
    build_routes_dispatch_payload,
    build_routes_timeout_deps,
    build_routes_timeout_payload,
)


async def run_bound_pre_model_phase_with_trace(
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
    desktop_started_published: bool,
    timeout_seconds: float,
    trace_route_stage: Any,
) -> Any:
    return await dispatch_pre_model_phase_with_trace(
        runtime,
        payload,
        route_payload=build_pre_model_phase_payload(
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            cleanup=cleanup,
            desktop_started_published=desktop_started_published,
            timeout_seconds=timeout_seconds,
            trace_route_stage=trace_route_stage,
        ),
        deps=build_pre_model_phase_deps(hooks),
    )


def run_bound_pre_model_observation_sidecars_with_trace(
    hooks: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    trace_route_stage: Any,
    observed_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    return dispatch_pre_model_observation_sidecars_with_trace(
        runtime,
        payload,
        route_payload=build_observation_payload(
            text=text,
            session_key=session_key,
            trace_route_stage=trace_route_stage,
            observed_at=observed_at,
        ),
        deps=build_observation_deps(hooks),
    )


async def run_bound_pre_model_routes_with_timeout(
    hooks: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    timeout_seconds: float,
    trace_route_stage: Any,
    runner: Any = None,
) -> Any:
    return await dispatch_pre_model_routes_with_timeout(
        runtime,
        payload,
        route_payload=build_routes_timeout_payload(
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            before_memory=before_memory,
            cleanup=cleanup,
            timeout_seconds=timeout_seconds,
            trace_route_stage=trace_route_stage,
        ),
        deps=build_routes_timeout_deps(hooks, runner=runner),
    )


async def run_bound_pre_model_routes(
    hooks: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
) -> Any:
    return await dispatch_pre_model_routes(
        runtime,
        payload,
        route_payload=build_routes_dispatch_payload(
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            before_memory=before_memory,
            cleanup=cleanup,
        ),
        deps=build_routes_dispatch_deps(hooks),
    )


__all__ = [
    "run_bound_pre_model_observation_sidecars_with_trace",
    "run_bound_pre_model_phase_with_trace",
    "run_bound_pre_model_routes",
    "run_bound_pre_model_routes_with_timeout",
]
