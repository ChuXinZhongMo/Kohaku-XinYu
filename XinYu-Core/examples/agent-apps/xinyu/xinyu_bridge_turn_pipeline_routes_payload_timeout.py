from __future__ import annotations

from typing import Any


def build_routes_timeout_payload(
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
) -> dict[str, Any]:
    return {
        "text": text,
        "session_key": session_key,
        "turn_id": turn_id,
        "turn_started_wall": turn_started_wall,
        "turn_started_at": turn_started_at,
        "before_memory": before_memory,
        "cleanup": cleanup,
        "timeout_seconds": timeout_seconds,
        "trace_route_stage": trace_route_stage,
    }


__all__ = ["build_routes_timeout_payload"]
