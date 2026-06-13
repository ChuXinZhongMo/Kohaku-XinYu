from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class NormalizedStateSidecarState:
    visible_turn: Any
    slow_state: Any
    slow_state_active: bool


def normalize_state_sidecar_state(live_state: Any) -> NormalizedStateSidecarState:
    slow_state = live_state.slow_state
    return NormalizedStateSidecarState(
        visible_turn=live_state.visible_turn,
        slow_state=slow_state,
        slow_state_active=bool(slow_state.active_policies),
    )
