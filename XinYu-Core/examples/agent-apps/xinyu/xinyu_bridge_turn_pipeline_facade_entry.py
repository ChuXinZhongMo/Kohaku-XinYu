from __future__ import annotations

from typing import Any

import xinyu_bridge_turn_pipeline_entry as _entry


def bind_entry_facade(hooks: Any) -> dict[str, Any]:
    def _safe_str(value: Any, default: str = "") -> str:
        return _entry.safe_str(value, default=default)

    def _timestamp_or_now_iso(value: Any) -> str:
        return _entry.timestamp_or_now_iso(hooks, value)

    def start_chat_turn_with_trace(
        runtime: Any,
        payload: dict[str, Any],
        *,
        text: str,
        session_key: str,
        turn_started_at: float,
    ) -> Any:
        return _entry.start_chat_turn_with_trace(
            hooks,
            runtime,
            payload,
            text=text,
            session_key=session_key,
            turn_started_at=turn_started_at,
        )

    def capture_memory_snapshot_with_trace(runtime: Any, *, trace_route_stage: Any) -> dict[str, Any]:
        return _entry.capture_memory_snapshot_with_trace(hooks, runtime, trace_route_stage=trace_route_stage)

    async def publish_chat_started_with_trace(
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
        return await _entry.publish_chat_started_with_trace(
            hooks,
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
        )

    return {
        "_safe_str": _safe_str,
        "_timestamp_or_now_iso": _timestamp_or_now_iso,
        "start_chat_turn_with_trace": start_chat_turn_with_trace,
        "capture_memory_snapshot_with_trace": capture_memory_snapshot_with_trace,
        "publish_chat_started_with_trace": publish_chat_started_with_trace,
    }
