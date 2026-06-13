from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from xinyu_bridge_pre_model_state import PreModelRouteResult


TraceRouteStage = Callable[..., Any]
PreModelRouteRunner = Callable[..., Awaitable[PreModelRouteResult]]


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
    trace_route_stage: TraceRouteStage,
    runner: PreModelRouteRunner,
    wait_for_func: Callable[..., Awaitable[Any]] = asyncio.wait_for,
) -> PreModelRouteResult:
    trace_route_stage(
        "pre_model_routes_started",
        notes=[f"timeout_seconds:{timeout_seconds}"],
    )
    try:
        result = await wait_for_func(
            runner(
                runtime,
                payload,
                text=text,
                session_key=session_key,
                turn_id=turn_id,
                turn_started_wall=turn_started_wall,
                turn_started_at=turn_started_at,
                before_memory=before_memory,
                cleanup=cleanup,
            ),
            timeout=timeout_seconds,
        )
        trace_route_stage("pre_model_routes_finished", status="ok")
        return result
    except asyncio.TimeoutError:
        timeout_note = f"pre_model_routes_timeout:{timeout_seconds}s"
        print(f"[xinyu_core_bridge] pre-model routes timed out: {timeout_note}", flush=True)
        trace_route_stage("pre_model_routes_finished", status="timeout", notes=[timeout_note])
        return PreModelRouteResult(
            response=None,
            event_sidecar={"notes": [timeout_note, "event_sourcing_unknown_after_timeout"]},
            v1_shadow={"notes": ["v1_shadow_skipped:pre_model_timeout"]},
            tinykernel_shadow={"notes": ["tinykernel_shadow_skipped:pre_model_timeout"]},
        )
    except Exception as exc:
        error_note = f"pre_model_routes_error:{type(exc).__name__}"
        print(f"[xinyu_core_bridge] pre-model routes failed: {type(exc).__name__}: {exc}", flush=True)
        trace_route_stage("pre_model_routes_finished", status="error", notes=[error_note])
        return PreModelRouteResult(
            response=None,
            event_sidecar={"notes": [error_note]},
            v1_shadow={"notes": ["v1_shadow_skipped:pre_model_error"]},
            tinykernel_shadow={"notes": ["tinykernel_shadow_skipped:pre_model_error"]},
        )
