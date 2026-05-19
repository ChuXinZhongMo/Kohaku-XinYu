from __future__ import annotations

from typing import Any

from xinyu_runtime_presence import read_runtime_presence_summary, record_turn_finished
from xinyu_turn_route_trace import read_turn_route_summary, record_turn_route_stage


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _current_turn(runtime: Any) -> dict[str, Any]:
    presence = read_runtime_presence_summary(runtime.xinyu_dir)
    route = read_turn_route_summary(runtime.xinyu_dir)
    current_turn = {
        "state": _safe_str(presence.get("current_turn_state"), "unknown"),
        "turn_id": _safe_str(presence.get("current_turn_id")),
        "kind": _safe_str(presence.get("current_turn_kind")),
        "source": _safe_str(presence.get("current_turn_source")),
        "relation": _safe_str(presence.get("current_turn_relation")),
        "started_at": _safe_str(presence.get("current_turn_started_at")),
        "age_seconds": int(presence.get("current_turn_age_seconds") or 0),
        "stale_running": bool(presence.get("stale_running")),
    }
    return {
        "presence": presence,
        "route": route,
        "current_turn": current_turn,
    }


def _intervention_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    return {
        "platform": "owner_intervention",
        "message_type": _safe_str(data.get("action"), "intervention"),
        "session_id": "owner_intervention",
        "user_id": "owner",
    }


def _record_intervention(
    runtime: Any,
    *,
    turn_id: str,
    action: str,
    stage: str,
    status: str,
    notes: list[str] | None = None,
) -> None:
    record_turn_route_stage(
        runtime.xinyu_dir,
        turn_id=turn_id,
        stage=stage,
        route="owner_intervention",
        status=status,
        payload=_intervention_payload({"action": action}),
        notes=[action] + list(notes or []),
    )


async def turn_current(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    del payload
    snapshot = _current_turn(runtime)
    return {
        "ok": True,
        "current_turn": snapshot["current_turn"],
        "route": snapshot["route"],
        "operator": runtime.health_snapshot().get("operator", {}),
    }


async def turn_cancel(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = _current_turn(runtime)
    current = snapshot["current_turn"]
    turn_id = _safe_str(current.get("turn_id")) or _safe_str(snapshot["route"].get("last_turn_id"))
    _record_intervention(runtime, turn_id=turn_id, action="cancel", stage="intervention_requested", status="running")
    if not turn_id or current.get("state") not in {"running", "stale_running"}:
        _record_intervention(
            runtime,
            turn_id=turn_id,
            action="cancel",
            stage="intervention_rejected",
            status="rejected",
            notes=["no_running_turn"],
        )
        return {"ok": False, "applied": False, "reason": "no_running_turn", "current_turn": current}
    notes = ["owner_intervention_cancel"]
    record_turn_finished(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply="",
        elapsed_ms=int(current.get("age_seconds") or 0) * 1000,
        status="cancelled",
        notes=notes,
        memory_changed=False,
    )
    _record_intervention(
        runtime,
        turn_id=turn_id,
        action="cancel",
        stage="intervention_applied",
        status="applied",
        notes=notes,
    )
    return {"ok": True, "applied": True, "turn_id": turn_id, "notes": notes}


async def turn_retry_lightweight(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _record_conservative_action(runtime, payload, action="retry_lightweight")


async def turn_skip_sidecar(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _record_conservative_action(runtime, payload, action="skip_sidecar")


async def turn_continue(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _record_conservative_action(runtime, payload, action="continue")


async def turn_status_message(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    del payload
    snapshot = _current_turn(runtime)
    current = snapshot["current_turn"]
    route = snapshot["route"]
    status = _safe_str(current.get("state"), "unknown")
    stage = _safe_str(route.get("last_stage"), "unknown")
    age = int(current.get("age_seconds") or 0)
    if status in {"running", "stale_running"}:
        message = f"Current turn is {status} at {stage}, age {age}s."
    else:
        message = f"No running turn. Last stage is {stage}."
    turn_id = _safe_str(current.get("turn_id")) or _safe_str(route.get("last_turn_id"))
    _record_intervention(
        runtime,
        turn_id=turn_id,
        action="status_message",
        stage="intervention_requested",
        status="ok",
    )
    return {"ok": True, "message": message, "current_turn": current, "route": route}


async def _record_conservative_action(
    runtime: Any,
    payload: dict[str, Any] | None,
    *,
    action: str,
) -> dict[str, Any]:
    snapshot = _current_turn(runtime)
    current = snapshot["current_turn"]
    route = snapshot["route"]
    turn_id = _safe_str(current.get("turn_id")) or _safe_str(route.get("last_turn_id"))
    _record_intervention(runtime, turn_id=turn_id, action=action, stage="intervention_requested", status="running")
    if not turn_id:
        _record_intervention(
            runtime,
            turn_id=turn_id,
            action=action,
            stage="intervention_rejected",
            status="rejected",
            notes=["no_turn"],
        )
        return {"ok": False, "applied": False, "reason": "no_turn", "current_turn": current}
    metadata = payload if isinstance(payload, dict) else {}
    force = bool(metadata.get("force"))
    safe_timeout_stage = _safe_str(route.get("last_status")) == "timeout"
    if not force and not safe_timeout_stage:
        _record_intervention(
            runtime,
            turn_id=turn_id,
            action=action,
            stage="intervention_rejected",
            status="rejected",
            notes=["requires_timeout_stage_or_force"],
        )
        return {
            "ok": False,
            "applied": False,
            "reason": "requires_timeout_stage_or_force",
            "current_turn": current,
            "route": route,
        }
    _record_intervention(
        runtime,
        turn_id=turn_id,
        action=action,
        stage="intervention_applied",
        status="applied",
        notes=["operator_action_recorded"],
    )
    return {"ok": True, "applied": True, "turn_id": turn_id, "action": action, "notes": ["operator_action_recorded"]}
