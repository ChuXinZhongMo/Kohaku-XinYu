from __future__ import annotations

from typing import Any

from xinyu_bridge_intervention_payloads import conservative_reject_reason, current_or_last_turn_id
from xinyu_bridge_intervention_routes_common import current_turn_snapshot, record_intervention


async def turn_retry_lightweight(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _record_conservative_action(runtime, payload, action="retry_lightweight")


async def turn_skip_sidecar(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _record_conservative_action(runtime, payload, action="skip_sidecar")


async def turn_continue(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _record_conservative_action(runtime, payload, action="continue")


async def _record_conservative_action(
    runtime: Any,
    payload: dict[str, Any] | None,
    *,
    action: str,
) -> dict[str, Any]:
    snapshot = current_turn_snapshot(runtime)
    current = snapshot["current_turn"]
    route = snapshot["route"]
    turn_id = current_or_last_turn_id(current, route)
    record_intervention(runtime, turn_id=turn_id, action=action, stage="intervention_requested", status="running")
    if not turn_id:
        record_intervention(
            runtime,
            turn_id=turn_id,
            action=action,
            stage="intervention_rejected",
            status="rejected",
            notes=["no_turn"],
        )
        return {"ok": False, "applied": False, "reason": "no_turn", "current_turn": current}

    reason = conservative_reject_reason(payload, route)
    if reason:
        record_intervention(
            runtime,
            turn_id=turn_id,
            action=action,
            stage="intervention_rejected",
            status="rejected",
            notes=[reason],
        )
        return {
            "ok": False,
            "applied": False,
            "reason": reason,
            "current_turn": current,
            "route": route,
        }

    record_intervention(
        runtime,
        turn_id=turn_id,
        action=action,
        stage="intervention_applied",
        status="applied",
        notes=["operator_action_recorded"],
    )
    return {"ok": True, "applied": True, "turn_id": turn_id, "action": action, "notes": ["operator_action_recorded"]}
