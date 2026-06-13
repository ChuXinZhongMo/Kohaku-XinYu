from __future__ import annotations

from typing import Any

import xinyu_bridge_turn_pipeline_decisions as _decisions


def bind_decision_facade(hooks: Any) -> dict[str, Any]:
    def probe_semantic_fast_decision_with_trace(
        runtime: Any,
        payload: dict[str, Any],
        *,
        text: str,
        trace_route_stage: Any,
    ) -> dict[str, Any]:
        return _decisions.probe_semantic_fast_decision_with_trace(
            hooks,
            runtime,
            payload,
            text=text,
            trace_route_stage=trace_route_stage,
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
        return await _decisions.try_pre_slow_semantic_fast_route_with_trace(
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
        return await _decisions.try_initial_semantic_fast_route_with_trace(
            hooks,
            runtime,
            payload,
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            cleanup=cleanup,
            trace_route_stage=trace_route_stage,
        )

    return {
        "probe_semantic_fast_decision_with_trace": probe_semantic_fast_decision_with_trace,
        "try_pre_slow_semantic_fast_route_with_trace": try_pre_slow_semantic_fast_route_with_trace,
        "try_initial_semantic_fast_route_with_trace": try_initial_semantic_fast_route_with_trace,
    }
