"""Response models."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..types import JSONValue


@dataclass(frozen=True, slots=True)
class DraftReply:
    text: str
    source: str
    notes: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, JSONValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FinalReply:
    text: str
    accepted: bool = True
    notes: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, JSONValue] = field(default_factory=dict)

