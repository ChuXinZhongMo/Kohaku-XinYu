from __future__ import annotations

from typing import Any

from xinyu_bridge_health_diagnostics_service import HealthDiagnosticsService
from xinyu_bridge_intervention_payloads import current_or_last_turn_id, status_message
from xinyu_bridge_intervention_routes_common import current_turn_snapshot, record_intervention


async def turn_current(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await HealthDiagnosticsService.turn_current(
        runtime,
        payload,
        current_turn_snapshot_func=current_turn_snapshot,
    )


async def turn_status_message(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    del payload
    snapshot = current_turn_snapshot(runtime)
    current = snapshot["current_turn"]
    route = snapshot["route"]
    turn_id = current_or_last_turn_id(current, route)
    record_intervention(
        runtime,
        turn_id=turn_id,
        action="status_message",
        stage="intervention_requested",
        status="ok",
    )
    return {"ok": True, "message": status_message(current, route), "current_turn": current, "route": route}
