from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from xinyu_bridge_state_mapping import DataclassMappingState


@dataclass
class PreModelRouteResult:
    response: dict[str, Any] | None
    event_sidecar: dict[str, Any]
    v1_shadow: dict[str, Any]
    tinykernel_shadow: dict[str, Any] = field(default_factory=dict)


@dataclass(eq=False)
class InitialSemanticFastState(DataclassMappingState):
    response: dict[str, Any] | None
    desktop_started_published: bool
    decision: dict[str, Any]


@dataclass(eq=False)
class PreModelPhaseState(DataclassMappingState):
    response: dict[str, Any] | None
    desktop_started_published: bool
    before_memory: dict[str, Any]
    curiosity_eval: dict[str, Any]
    private_thought_outcome: dict[str, Any]
    uncertainty_pause_reply: dict[str, Any]
    event_sidecar: dict[str, Any]
    v1_shadow: dict[str, Any]
    tinykernel_shadow: dict[str, Any]
