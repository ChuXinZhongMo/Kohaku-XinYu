from __future__ import annotations

from typing import Any

from xinyu_bridge_turn_pipeline_routes_pre_model_bindings import (
    run_bound_pre_model_observation_sidecars_with_trace,
    run_bound_pre_model_phase_with_trace,
    run_bound_pre_model_routes,
    run_bound_pre_model_routes_with_timeout,
)
from xinyu_bridge_turn_pipeline_routes_runtime_bindings import (
    looks_like_runtime_repair_status_question as _looks_like_runtime_repair_status_question,
    run_bound_runtime_repair_status_turn,
    run_bound_tinykernel_shadow,
    tcp_connect as _tcp_connect,
)


async def run_pre_model_phase_with_trace(
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
    return await run_bound_pre_model_phase_with_trace(
        hooks,
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        cleanup=cleanup,
        desktop_started_published=desktop_started_published,
        timeout_seconds=timeout_seconds,
        trace_route_stage=trace_route_stage,
    )


def run_pre_model_observation_sidecars_with_trace(
    hooks: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    trace_route_stage: Any,
    observed_at: str | None = None,
) -> dict[str, dict[str, Any]]:
    return run_bound_pre_model_observation_sidecars_with_trace(
        hooks,
        runtime,
        payload,
        text=text,
        session_key=session_key,
        trace_route_stage=trace_route_stage,
        observed_at=observed_at,
    )


async def run_pre_model_routes_with_timeout(
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
    return await run_bound_pre_model_routes_with_timeout(
        hooks,
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
        runner=runner,
    )


async def run_pre_model_routes(
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
    return await run_bound_pre_model_routes(
        hooks,
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
    )


async def run_tinykernel_shadow(
    hooks: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    turn_id: str,
    observed_at: str,
) -> dict[str, Any]:
    return await run_bound_tinykernel_shadow(
        hooks,
        runtime,
        payload,
        text=text,
        turn_id=turn_id,
        observed_at=observed_at,
    )


async def maybe_handle_runtime_repair_status_turn(
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
    event_sidecar: dict[str, Any],
) -> dict[str, Any] | None:
    return await run_bound_runtime_repair_status_turn(
        hooks,
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
    )


def looks_like_runtime_repair_status_question(text: str) -> bool:
    return _looks_like_runtime_repair_status_question(text)


def tcp_connect(host: str, port: int, timeout: float = 0.5) -> bool:
    return _tcp_connect(host, port, timeout=timeout)
