from __future__ import annotations

from typing import Any


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def current_turn_from_presence(presence: dict[str, Any]) -> dict[str, Any]:
    return {
        "state": safe_str(presence.get("current_turn_state"), "unknown"),
        "turn_id": safe_str(presence.get("current_turn_id")),
        "kind": safe_str(presence.get("current_turn_kind")),
        "source": safe_str(presence.get("current_turn_source")),
        "relation": safe_str(presence.get("current_turn_relation")),
        "started_at": safe_str(presence.get("current_turn_started_at")),
        "age_seconds": int(presence.get("current_turn_age_seconds") or 0),
        "stale_running": bool(presence.get("stale_running")),
    }


def intervention_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    return {
        "platform": "owner_intervention",
        "message_type": safe_str(data.get("action"), "intervention"),
        "session_id": "owner_intervention",
        "user_id": "owner",
    }


def current_or_last_turn_id(current: dict[str, Any], route: dict[str, Any]) -> str:
    return safe_str(current.get("turn_id")) or safe_str(route.get("last_turn_id"))


def status_message(current: dict[str, Any], route: dict[str, Any]) -> str:
    status = safe_str(current.get("state"), "unknown")
    stage = safe_str(route.get("last_stage"), "unknown")
    age = int(current.get("age_seconds") or 0)
    if status in {"running", "stale_running"}:
        return f"Current turn is {status} at {stage}, age {age}s."
    return f"No running turn. Last stage is {stage}."


def conservative_reject_reason(payload: dict[str, Any] | None, route: dict[str, Any]) -> str:
    metadata = payload if isinstance(payload, dict) else {}
    if bool(metadata.get("force")):
        return ""
    if safe_str(route.get("last_status")) == "timeout":
        return ""
    return "requires_timeout_stage_or_force"
