from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from xinyu_bridge_route_observer import TurnRouteObserver
from xinyu_bridge_time_utils import timestamp_or_now_iso
from xinyu_bridge_turn_state import ChatTurnStartState
from xinyu_bridge_values import safe_str
from xinyu_runtime_presence import record_turn_started


TraceRouteStage = Callable[..., Any]


def start_chat_turn_with_trace(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_started_at: float,
    record_started_func: Callable[..., dict[str, Any]] = record_turn_started,
    route_observer_cls: type[Any] = TurnRouteObserver,
    safe_str_func: Callable[..., str] = safe_str,
) -> ChatTurnStartState:
    presence_start = record_started_func(
        runtime.xinyu_dir,
        payload=payload,
        text=text,
        session_key=session_key,
        active_sessions=len(runtime._sessions),
    )
    turn_id = safe_str_func(presence_start.get("turn_id"))
    route_observer = route_observer_cls(
        runtime.xinyu_dir,
        turn_id=turn_id,
        payload=payload,
        started_at=turn_started_at,
    )
    trace_route_stage = route_observer.record
    trace_route_stage(
        "turn_started",
        elapsed_ms=0,
        notes=[safe_str_func(note) for note in presence_start.get("notes", [])[:4]],
    )
    return ChatTurnStartState(
        presence_start=presence_start,
        turn_id=turn_id,
        trace_route_stage=trace_route_stage,
    )


async def publish_chat_started_with_trace(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    active_sessions: int,
    trace_route_stage: TraceRouteStage,
    route: str = "",
    timeout_seconds: float = 1.5,
    wait_for_func: Callable[..., Any] = asyncio.wait_for,
    timestamp_func: Callable[..., str] = timestamp_or_now_iso,
) -> bool:
    stage_kwargs = {"route": route} if route else {}
    trace_route_stage("desktop_started_publish_started", **stage_kwargs)
    try:
        await wait_for_func(
            runtime._desktop_publish_chat_started(
                payload,
                text=text,
                session_key=session_key,
                turn_id=turn_id,
                started_at=timestamp_func(turn_started_wall),
                active_sessions=active_sessions,
            ),
            timeout=timeout_seconds,
        )
        trace_route_stage("desktop_started_publish_finished", **stage_kwargs, status="ok")
        return True
    except Exception as exc:
        print(f"[xinyu_core_bridge] desktop chat started publish skipped: {type(exc).__name__}: {exc}", flush=True)
        trace_route_stage(
            "desktop_started_publish_finished",
            **stage_kwargs,
            status="error",
            notes=[f"desktop_publish_error:{type(exc).__name__}"],
        )
        return False
