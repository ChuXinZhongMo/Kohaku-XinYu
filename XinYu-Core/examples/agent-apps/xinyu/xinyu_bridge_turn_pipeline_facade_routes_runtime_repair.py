from __future__ import annotations

from typing import Any

import xinyu_bridge_turn_pipeline_routes as _routes


def bind_runtime_repair_route_facade(hooks: Any) -> dict[str, Any]:
    async def _maybe_handle_runtime_repair_status_turn(
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
        return await _routes.maybe_handle_runtime_repair_status_turn(
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

    def _looks_like_runtime_repair_status_question(text: str) -> bool:
        return _routes.looks_like_runtime_repair_status_question(text)

    def _tcp_connect(host: str, port: int, timeout: float = 0.5) -> bool:
        return _routes.tcp_connect(host, port, timeout=timeout)

    return {
        "_maybe_handle_runtime_repair_status_turn": _maybe_handle_runtime_repair_status_turn,
        "_looks_like_runtime_repair_status_question": _looks_like_runtime_repair_status_question,
        "_tcp_connect": _tcp_connect,
    }


__all__ = ["bind_runtime_repair_route_facade"]
