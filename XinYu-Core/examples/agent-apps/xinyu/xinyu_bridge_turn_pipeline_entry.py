from __future__ import annotations

from typing import Any

from xinyu_bridge_turn_start import (
    publish_chat_started_with_trace as _runtime_publish_chat_started_with_trace,
    start_chat_turn_with_trace as _runtime_start_chat_turn_with_trace,
)


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def timestamp_or_now_iso(hooks: Any, value: Any) -> str:
    text = hooks._safe_str(value).strip()
    if text:
        try:
            return hooks.datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone().isoformat()
        except ValueError:
            pass
    return hooks.datetime.now().astimezone().isoformat()


def start_chat_turn_with_trace(
    hooks: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_started_at: float,
) -> Any:
    return _runtime_start_chat_turn_with_trace(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_started_at=turn_started_at,
        record_started_func=hooks.record_turn_started,
        route_observer_cls=hooks.TurnRouteObserver,
        safe_str_func=hooks._safe_str,
    )


def capture_memory_snapshot_with_trace(hooks: Any, runtime: Any, *, trace_route_stage: Any) -> dict[str, Any]:
    trace_route_stage("memory_snapshot_started")
    snapshot = hooks._memory_snapshot(runtime.memory_root)
    trace_route_stage("memory_snapshot_finished", status="ok")
    return snapshot


async def publish_chat_started_with_trace(
    hooks: Any,
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    active_sessions: int,
    trace_route_stage: Any,
    route: str = "",
    timeout_seconds: float = 1.5,
) -> bool:
    return await _runtime_publish_chat_started_with_trace(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        active_sessions=active_sessions,
        trace_route_stage=trace_route_stage,
        route=route,
        timeout_seconds=timeout_seconds,
        wait_for_func=hooks.asyncio.wait_for,
        timestamp_func=hooks._timestamp_or_now_iso,
    )
