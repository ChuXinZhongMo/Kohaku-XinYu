from __future__ import annotations

from typing import Any

from xinyu_bridge_pre_model_observations import (
    run_pre_model_observation_sidecars_with_trace as _runtime_run_pre_model_observation_sidecars_with_trace,
)
from xinyu_bridge_pre_model_phase import run_pre_model_phase_with_trace as _runtime_run_pre_model_phase_with_trace
from xinyu_bridge_pre_model_routes import run_pre_model_routes as _runtime_run_pre_model_routes
from xinyu_bridge_pre_model_timeout import (
    run_pre_model_routes_with_timeout as _runtime_run_pre_model_routes_with_timeout,
)


async def dispatch_pre_model_phase_with_trace(
    runtime: Any,
    payload: dict[str, Any],
    *,
    route_payload: dict[str, Any],
    deps: dict[str, Any],
) -> Any:
    return await _runtime_run_pre_model_phase_with_trace(runtime, payload, **route_payload, **deps)


def dispatch_pre_model_observation_sidecars_with_trace(
    runtime: Any,
    payload: dict[str, Any],
    *,
    route_payload: dict[str, Any],
    deps: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return _runtime_run_pre_model_observation_sidecars_with_trace(runtime, payload, **route_payload, **deps)


async def dispatch_pre_model_routes_with_timeout(
    runtime: Any,
    payload: dict[str, Any],
    *,
    route_payload: dict[str, Any],
    deps: dict[str, Any],
) -> Any:
    return await _runtime_run_pre_model_routes_with_timeout(runtime, payload, **route_payload, **deps)


async def dispatch_pre_model_routes(
    runtime: Any,
    payload: dict[str, Any],
    *,
    route_payload: dict[str, Any],
    deps: dict[str, Any],
) -> Any:
    return await _runtime_run_pre_model_routes(runtime, payload, **route_payload, **deps)


__all__ = [
    "dispatch_pre_model_observation_sidecars_with_trace",
    "dispatch_pre_model_phase_with_trace",
    "dispatch_pre_model_routes",
    "dispatch_pre_model_routes_with_timeout",
]
