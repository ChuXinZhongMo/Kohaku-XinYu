"""Backend-agnostic vector-store protocol."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from ..types import Embedding, HealthState, JSONValue, PrivacyScope, ServiceHealth, SourceChannel, coerce_enum
from .models import MemoryChunk, MemoryQuery, MemorySearchResult


@dataclass(frozen=True, slots=True)
class VectorRecord:
    chunk: MemoryChunk
    embedding: Embedding


class VectorStore(Protocol):
    async def upsert(self, records: tuple[VectorRecord, ...]) -> None:
        """Insert or update vector records."""

    async def search(self, query: MemoryQuery, embedding: Embedding) -> tuple[MemorySearchResult, ...]:
        """Search records by vector and metadata filters."""

    async def delete(self, chunk_ids: tuple[str, ...]) -> None:
        """Delete records by chunk id."""

    async def health(self) -> ServiceHealth:
        """Return vector-store health."""


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}

    async def upsert(self, records: tuple[VectorRecord, ...]) -> None:
        for record in records:
            self._records[record.chunk.chunk_id] = record

    async def search(self, query: MemoryQuery, embedding: Embedding) -> tuple[MemorySearchResult, ...]:
        scored: list[MemorySearchResult] = []
        for record in self._records.values():
            if query.layers and record.chunk.layer not in query.layers:
                continue
            if query.tags and not set(query.tags).intersection(record.chunk.tags):
                continue
            if query.source_channels and _metadata_source_channel(record.chunk) not in query.source_channels:
                continue
            if query.privacy_scopes and _metadata_privacy_scope(record.chunk) not in query.privacy_scopes:
                continue
            score = cosine_similarity(embedding, record.embedding)
            if score >= query.min_score:
                scored.append(MemorySearchResult(chunk=record.chunk, score=score, reason="vector"))
        scored.sort(key=lambda item: item.score, reverse=True)
        return tuple(scored[: max(0, query.limit)])

    async def delete(self, chunk_ids: tuple[str, ...]) -> None:
        for chunk_id in chunk_ids:
            self._records.pop(chunk_id, None)

    async def health(self) -> ServiceHealth:
        return ServiceHealth(
            component="in_memory_vector_store",
            state=HealthState.OK,
            details={"records": len(self._records)},
        )


def cosine_similarity(left: Embedding, right: Embedding) -> float:
    if not left or not right:
        return 0.0
    limit = min(len(left), len(right))
    dot = sum(left[index] * right[index] for index in range(limit))
    left_norm = math.sqrt(sum(value * value for value in left[:limit]))
    right_norm = math.sqrt(sum(value * value for value in right[:limit]))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def metadata_for_chunk(chunk: MemoryChunk) -> dict[str, JSONValue]:
    data = chunk.to_json()
    data.pop("text", None)
    return data


def _metadata_source_channel(chunk: MemoryChunk) -> SourceChannel:
    return coerce_enum(SourceChannel, chunk.metadata.get("source_channel"), SourceChannel.UNKNOWN)


def _metadata_privacy_scope(chunk: MemoryChunk) -> PrivacyScope:
    return coerce_enum(PrivacyScope, chunk.metadata.get("privacy_scope"), PrivacyScope.UNKNOWN)
