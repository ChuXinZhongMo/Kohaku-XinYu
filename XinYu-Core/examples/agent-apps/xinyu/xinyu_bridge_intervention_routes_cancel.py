from __future__ import annotations

from typing import Any

from xinyu_bridge_intervention_payloads import current_or_last_turn_id
from xinyu_bridge_intervention_routes_common import current_turn_snapshot, record_intervention
from xinyu_runtime_presence import record_turn_finished


async def turn_cancel(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    del payload
    snapshot = current_turn_snapshot(runtime)
    current = snapshot["current_turn"]
    turn_id = current_or_last_turn_id(current, snapshot["route"])
    record_intervention(runtime, turn_id=turn_id, action="cancel", stage="intervention_requested", status="running")
    if not turn_id or current.get("state") not in {"running", "stale_running"}:
        record_intervention(
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
    record_intervention(
        runtime,
        turn_id=turn_id,
        action="cancel",
        stage="intervention_applied",
        status="applied",
        notes=notes,
    )
    return {"ok": True, "applied": True, "turn_id": turn_id, "notes": notes}
