"""Memory domain models."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..types import JSONValue, MemoryId, MemoryLayer, MemoryWriteMode, PrivacyScope, SourceChannel, TraceContext


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


@dataclass(frozen=True, slots=True)
class MemoryEvent:
    event_id: MemoryId
    timestamp: str
    source_channel: SourceChannel
    privacy_scope: PrivacyScope
    actor_hash: str
    text: str
    salience: int = 0
    layers: tuple[MemoryLayer, ...] = field(default_factory=tuple)
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    @classmethod
    def from_text(
        cls,
        *,
        text: str,
        timestamp: str,
        source_channel: SourceChannel,
        privacy_scope: PrivacyScope,
        actor_hash: str = "",
        salience: int = 0,
        layers: tuple[MemoryLayer, ...] = (),
        metadata: dict[str, JSONValue] | None = None,
    ) -> "MemoryEvent":
        seed = f"{timestamp}|{source_channel.value}|{actor_hash}|{text}"
        return cls(
            event_id=f"evt-{sha256_text(seed)[:16]}",
            timestamp=timestamp,
            source_channel=source_channel,
            privacy_scope=privacy_scope,
            actor_hash=actor_hash,
            text=text,
            salience=salience,
            layers=layers,
            metadata=metadata or {},
        )

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "source_channel": self.source_channel.value,
            "privacy_scope": self.privacy_scope.value,
            "actor_hash": self.actor_hash,
            "text": self.text,
            "text_hash": sha256_text(self.text),
            "salience": self.salience,
            "layers": [layer.value for layer in self.layers],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class MemoryChunk:
    chunk_id: MemoryId
    text: str
    layer: MemoryLayer
    source_event_id: MemoryId = ""
    source_path: str = ""
    timestamp: str = ""
    salience: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    @classmethod
    def stable(
        cls,
        *,
        text: str,
        layer: MemoryLayer,
        source_event_id: str = "",
        source_path: str = "",
        timestamp: str = "",
        salience: int = 0,
        tags: tuple[str, ...] = (),
        metadata: dict[str, JSONValue] | None = None,
    ) -> "MemoryChunk":
        seed = f"{layer.value}|{source_event_id}|{source_path}|{text}"
        return cls(
            chunk_id=f"mem-{sha256_text(seed)[:20]}",
            text=text,
            layer=layer,
            source_event_id=source_event_id,
            source_path=source_path,
            timestamp=timestamp,
            salience=salience,
            tags=tags,
            metadata=metadata or {},
        )

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "layer": self.layer.value,
            "source_event_id": self.source_event_id,
            "source_path": self.source_path,
            "timestamp": self.timestamp,
            "salience": self.salience,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class MemoryQuery:
    text: str
    layers: tuple[MemoryLayer, ...] = field(default_factory=tuple)
    source_channels: tuple[SourceChannel, ...] = field(default_factory=tuple)
    privacy_scopes: tuple[PrivacyScope, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    limit: int = 8
    min_score: float = 0.0
    trace: TraceContext | None = None


@dataclass(frozen=True, slots=True)
class MemorySearchResult:
    chunk: MemoryChunk
    score: float
    reason: str = ""

    def to_json(self) -> dict[str, JSONValue]:
        return {"chunk": self.chunk.to_json(), "score": self.score, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    role: str
    text: str
    timestamp: str = ""
    event_id: MemoryId = ""
    trace_id: str = ""
    source_channel: SourceChannel = SourceChannel.UNKNOWN
    privacy_scope: PrivacyScope = PrivacyScope.UNKNOWN


@dataclass(frozen=True, slots=True)
class MemoryWriteIntent:
    text: str
    layer: MemoryLayer
    mode: MemoryWriteMode
    timestamp: str
    source_event_id: str = ""
    salience: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, JSONValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConsolidationCandidate:
    candidate_id: str
    chunks: tuple[MemoryChunk, ...]
    proposed_summary: str
    target_layer: MemoryLayer
    confidence: float
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "candidate_id": self.candidate_id,
            "chunk_ids": [chunk.chunk_id for chunk in self.chunks],
            "proposed_summary": self.proposed_summary,
            "target_layer": self.target_layer.value,
            "confidence": self.confidence,
            "notes": list(self.notes),
        }
