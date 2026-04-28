"""High-level memory API for v1 runtime layers."""

from __future__ import annotations

from pathlib import Path

from ..types import HealthState, MemoryWriteMode, ServiceHealth
from .embeddings import EmbeddingProvider, HashEmbeddingProvider
from .jsonl_store import JsonlMemoryStore
from .models import MemoryEvent, MemoryQuery, MemorySearchResult, MemoryWriteIntent
from .retriever import MemoryRetriever
from .vector_store import InMemoryVectorStore, VectorRecord, VectorStore
from .writer import MemoryWriteResult, MemoryWriter


class MemoryOrchestrator:
    def __init__(
        self,
        *,
        runtime_root: Path,
        vector_store: VectorStore | None = None,
        embeddings: EmbeddingProvider | None = None,
    ) -> None:
        self._jsonl_store = JsonlMemoryStore(runtime_root / "memory")
        self._embeddings = embeddings or HashEmbeddingProvider()
        self._vector_store = vector_store or InMemoryVectorStore()
        self._retriever = MemoryRetriever(self._vector_store, self._embeddings)
        self._writer = MemoryWriter(self._jsonl_store, self._vector_store, self._embeddings)

    async def bootstrap_from_chunks(self, chunks: tuple[VectorRecord, ...]) -> None:
        await self._vector_store.upsert(chunks)

    async def record_event(self, event: MemoryEvent) -> MemoryWriteResult:
        return await self._writer.write_event(event)

    async def write(self, intent: MemoryWriteIntent) -> MemoryWriteResult:
        if intent.mode is MemoryWriteMode.NONE:
            return MemoryWriteResult(accepted=False, notes=("write_mode_none",))
        return await self._writer.write_intent(intent)

    async def retrieve(self, query: MemoryQuery) -> tuple[MemorySearchResult, ...]:
        return await self._retriever.retrieve(query)

    async def health(self) -> ServiceHealth:
        try:
            return await self._vector_store.health()
        except Exception as exc:
            return ServiceHealth(component="memory_orchestrator", state=HealthState.DEGRADED, message=str(exc))

