from __future__ import annotations

from typing import Any

from xinyu_bridge_turn_pipeline_routes_payload import (
    build_runtime_repair_status_deps,
    build_runtime_repair_status_payload,
    build_tinykernel_deps,
    build_tinykernel_payload,
)
from xinyu_bridge_turn_pipeline_routes_response import (
    looks_like_runtime_repair_status_question,
    maybe_runtime_repair_status_response,
    run_tinykernel_shadow_response,
    tcp_connect,
)


async def run_bound_tinykernel_shadow(
    hooks: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    turn_id: str,
    observed_at: str,
) -> dict[str, Any]:
    return await run_tinykernel_shadow_response(
        runtime,
        payload,
        route_payload=build_tinykernel_payload(
            text=text,
            turn_id=turn_id,
            observed_at=observed_at,
        ),
        deps=build_tinykernel_deps(hooks),
    )


async def run_bound_runtime_repair_status_turn(
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
    return await maybe_runtime_repair_status_response(
        runtime,
        payload,
        route_payload=build_runtime_repair_status_payload(
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            before_memory=before_memory,
            cleanup=cleanup,
            event_sidecar=event_sidecar,
        ),
        deps=build_runtime_repair_status_deps(hooks),
    )


__all__ = [
    "looks_like_runtime_repair_status_question",
    "run_bound_runtime_repair_status_turn",
    "run_bound_tinykernel_shadow",
    "tcp_connect",
]
