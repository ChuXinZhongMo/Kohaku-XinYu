"""Reasoning models."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..emotion.models import EmotionState
from ..gateway.models import InboundTurn
from ..memory.models import ConversationMessage, MemorySearchResult
from ..routing.hybrid_router import RouteDecision
from ..types import JSONValue, ResourceUsage


@dataclass(frozen=True, slots=True)
class ReasoningRequest:
    turn: InboundTurn
    route: RouteDecision
    memories: tuple[MemorySearchResult, ...] = field(default_factory=tuple)
    recent_messages: tuple[ConversationMessage, ...] = field(default_factory=tuple)
    emotion_state: EmotionState | None = None
    system_context: str = ""


@dataclass(frozen=True, slots=True)
class ReasoningResult:
    draft: str
    memory_changed: bool | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    usage: ResourceUsage = field(default_factory=ResourceUsage)
    metadata: dict[str, JSONValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConflictReport:
    has_conflict: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    severity: float = 0.0
