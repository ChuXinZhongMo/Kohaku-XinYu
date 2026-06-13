from __future__ import annotations

from typing import Any


def build_pre_model_phase_payload(
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
) -> dict[str, Any]:
    return {
        "text": text,
        "session_key": session_key,
        "turn_id": turn_id,
        "turn_started_wall": turn_started_wall,
        "turn_started_at": turn_started_at,
        "cleanup": cleanup,
        "desktop_started_published": desktop_started_published,
        "timeout_seconds": timeout_seconds,
        "trace_route_stage": trace_route_stage,
    }


def build_routes_dispatch_payload(
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
) -> dict[str, Any]:
    return {
        "text": text,
        "session_key": session_key,
        "turn_id": turn_id,
        "turn_started_wall": turn_started_wall,
        "turn_started_at": turn_started_at,
        "before_memory": before_memory,
        "cleanup": cleanup,
    }


def build_runtime_repair_status_payload(
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
) -> dict[str, Any]:
    return {
        "text": text,
        "session_key": session_key,
        "turn_id": turn_id,
        "turn_started_wall": turn_started_wall,
        "turn_started_at": turn_started_at,
        "before_memory": before_memory,
        "cleanup": cleanup,
        "event_sidecar": event_sidecar,
    }


__all__ = [
    "build_pre_model_phase_payload",
    "build_routes_dispatch_payload",
    "build_runtime_repair_status_payload",
]
