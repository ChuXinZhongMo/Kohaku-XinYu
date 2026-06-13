from __future__ import annotations

from typing import Any

import xinyu_bridge_turn_pipeline_routes as _routes


def bind_pre_model_route_facade(hooks: Any) -> dict[str, Any]:
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
        trace_route_stage: Any,
    ) -> Any:
        return await _routes.run_pre_model_phase_with_trace(
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
        runtime: Any,
        payload: dict[str, Any],
        *,
        text: str,
        session_key: str,
        trace_route_stage: Any,
        observed_at: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        return _routes.run_pre_model_observation_sidecars_with_trace(
            hooks,
            runtime,
            payload,
            text=text,
            session_key=session_key,
            trace_route_stage=trace_route_stage,
            observed_at=observed_at,
        )

    async def run_pre_model_routes_with_timeout(
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
        return await _routes.run_pre_model_routes_with_timeout(
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
        return await _routes.run_pre_model_routes(
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

    return {
        "run_pre_model_phase_with_trace": run_pre_model_phase_with_trace,
        "run_pre_model_observation_sidecars_with_trace": run_pre_model_observation_sidecars_with_trace,
        "run_pre_model_routes_with_timeout": run_pre_model_routes_with_timeout,
        "run_pre_model_routes": run_pre_model_routes,
    }


__all__ = ["bind_pre_model_route_facade"]
