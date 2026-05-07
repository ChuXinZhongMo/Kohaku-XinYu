from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from xinyu_memory_event_sourcing import record_chat_event


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


@dataclass
class PreModelRouteResult:
    response: dict[str, Any] | None
    event_sidecar: dict[str, Any]
    v1_shadow: dict[str, Any]


async def run_pre_model_routes(
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
) -> PreModelRouteResult:
    event_sidecar: dict[str, Any] = {"notes": ["event_sourcing_not_run"]}
    v1_shadow: dict[str, Any] = {"notes": []}
    try:
        event_sidecar = record_chat_event(runtime.xinyu_dir, payload, text=text)
    except Exception as exc:
        print(f"[xinyu_core_bridge] event sourcing sidecar failed: {exc}", flush=True)
        event_sidecar = {"notes": [f"event_sourcing_error:{type(exc).__name__}"]}

    action_layer_response = await runtime._maybe_handle_action_layer_turn(
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
    if action_layer_response is not None:
        return PreModelRouteResult(action_layer_response, event_sidecar, v1_shadow)

    recent_action_followup = await runtime._maybe_handle_recent_action_followup_turn(
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
    if recent_action_followup is not None:
        return PreModelRouteResult(recent_action_followup, event_sidecar, v1_shadow)

    action_digest_followup = await runtime._maybe_handle_action_digest_followup_turn(
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
    if action_digest_followup is not None:
        return PreModelRouteResult(action_digest_followup, event_sidecar, v1_shadow)

    v1_canary_response = await runtime._maybe_handle_v1_canary_turn(
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
    if v1_canary_response is not None:
        return PreModelRouteResult(v1_canary_response, event_sidecar, v1_shadow)

    v1_shadow = await runtime._run_v1_shadow(payload, text=text)
    return PreModelRouteResult(None, event_sidecar, v1_shadow)
