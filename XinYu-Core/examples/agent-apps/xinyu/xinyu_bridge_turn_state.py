from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from xinyu_bridge_state_mapping import DataclassMappingState


@dataclass(eq=False)
class ChatTurnStartState(DataclassMappingState):
    presence_start: dict[str, Any]
    turn_id: str
    trace_route_stage: Any
