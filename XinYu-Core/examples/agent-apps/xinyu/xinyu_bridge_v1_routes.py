from __future__ import annotations

from typing import Any

import v1_canary_gate
from xinyu_bridge_v1_payloads import V1_CANARY_ACK_TEXTS, V1_CANARY_GREETING_TEXTS
from xinyu_bridge_v1_payloads import V1_OWNER_SIMPLE_CANARY_ENV
from xinyu_bridge_v1_payloads import safe_str as _safe_str
from xinyu_bridge_v1_provider import ensure_app as _ensure_app_impl
from xinyu_bridge_v1_provider import health as _health_impl
from xinyu_bridge_v1_route_adapter import canary_payload_allowed_impl, handle_canary_turn_impl
from xinyu_bridge_v1_route_adapter import record_shadow_readiness_impl, run_shadow_impl
from xinyu_v1_canary_readiness import record_v1_shadow_observation


def health(runtime: Any) -> dict[str, Any]:
    return _health_impl(runtime)


def ensure_app(runtime: Any) -> Any:
    return _ensure_app_impl(runtime)


def record_shadow_readiness(
    runtime: Any,
    shadow_payload: dict[str, Any],
    *,
    accepted: bool,
    route: str,
    trace_id: str,
    elapsed_ms: int,
    error: str = "",
) -> list[str]:
    return record_shadow_readiness_impl(
        runtime,
        shadow_payload,
        accepted=accepted,
        route=route,
        trace_id=trace_id,
        elapsed_ms=elapsed_ms,
        error=error,
        record_observation_func=record_v1_shadow_observation,
        safe_str_func=_safe_str,
    )


async def run_shadow(runtime: Any, payload: dict[str, Any], *, text: str) -> dict[str, Any]:
    return await run_shadow_impl(
        runtime,
        payload,
        text=text,
        ensure_app_func=ensure_app,
        record_shadow_readiness_func=record_shadow_readiness,
        safe_str_func=_safe_str,
    )


def canary_payload_allowed(runtime: Any, payload: dict[str, Any], text: str) -> tuple[bool, list[str]]:
    return canary_payload_allowed_impl(
        runtime,
        payload,
        text,
        canary_gate_func=v1_canary_gate.canary_payload_allowed,
        owner_simple_canary_env=V1_OWNER_SIMPLE_CANARY_ENV,
        greeting_texts=V1_CANARY_GREETING_TEXTS,
        ack_texts=V1_CANARY_ACK_TEXTS,
    )


async def handle_canary_turn(
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
    return await handle_canary_turn_impl(
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
        canary_payload_allowed_func=canary_payload_allowed,
        ensure_app_func=ensure_app,
        safe_str_func=_safe_str,
    )


__all__ = [
    "V1_CANARY_ACK_TEXTS",
    "V1_CANARY_GREETING_TEXTS",
    "V1_OWNER_SIMPLE_CANARY_ENV",
    "canary_payload_allowed",
    "ensure_app",
    "handle_canary_turn",
    "health",
    "record_shadow_readiness",
    "run_shadow",
]
