from __future__ import annotations

from typing import Any

from xinyu_bridge_intervention_payloads import current_turn_from_presence, intervention_payload
from xinyu_runtime_presence import read_runtime_presence_summary
from xinyu_turn_route_trace import read_turn_route_summary, record_turn_route_stage


def current_turn_snapshot(runtime: Any) -> dict[str, Any]:
    presence = read_runtime_presence_summary(runtime.xinyu_dir)
    route = read_turn_route_summary(runtime.xinyu_dir)
    return {
        "presence": presence,
        "route": route,
        "current_turn": current_turn_from_presence(presence),
    }


def intervention_trace_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    return intervention_payload(payload)


def record_intervention(
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
        payload=intervention_trace_payload({"action": action}),
        notes=[action] + list(notes or []),
    )
