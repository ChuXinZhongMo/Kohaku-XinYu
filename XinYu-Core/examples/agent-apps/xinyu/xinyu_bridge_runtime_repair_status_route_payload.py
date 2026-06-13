from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeRepairStatusRoutePayload:
    text: str
    session_key: str
    turn_id: str
    turn_started_wall: str
    turn_started_at: float
    before_memory: dict[str, Any]
    cleanup: dict[str, Any]
    event_sidecar: dict[str, Any]


def build_runtime_repair_status_route_payload(
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
) -> RuntimeRepairStatusRoutePayload:
    return RuntimeRepairStatusRoutePayload(
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
    )


__all__ = [
    "RuntimeRepairStatusRoutePayload",
    "build_runtime_repair_status_route_payload",
]
