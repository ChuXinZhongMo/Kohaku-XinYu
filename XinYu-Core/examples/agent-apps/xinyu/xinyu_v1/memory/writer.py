"""Memory write intent routing."""

from __future__ import annotations

from dataclasses import dataclass

from ..types import MemoryWriteMode
from .embeddings import EmbeddingProvider, HashEmbeddingProvider
from .jsonl_store import JsonlMemoryStore
from .models import MemoryChunk, MemoryEvent, MemoryWriteIntent
from .vector_store import VectorRecord, VectorStore


@dataclass(frozen=True, slots=True)
class MemoryWriteResult:
    accepted: bool
    event_written: bool = False
    chunk_written: bool = False
    vector_written: bool = False
    notes: tuple[str, ...] = ()


class MemoryWriter:
    def __init__(
        self,
        jsonl_store: JsonlMemoryStore,
        vector_store: VectorStore,
        embeddings: EmbeddingProvider | None = None,
    ) -> None:
        self._jsonl_store = jsonl_store
        self._vector_store = vector_store
        self._embeddings = embeddings or HashEmbeddingProvider()

    async def write_event(self, event: MemoryEvent) -> MemoryWriteResult:
        written = self._jsonl_store.append_event(event)
        return MemoryWriteResult(accepted=True, event_written=written, notes=("event_log",))

    async def write_intent(self, intent: MemoryWriteIntent) -> MemoryWriteResult:
        if intent.mode is MemoryWriteMode.NONE:
            return MemoryWriteResult(accepted=False, notes=("write_mode_none",))
        chunk = MemoryChunk.stable(
            text=intent.text,
            layer=intent.layer,
            source_event_id=intent.source_event_id,
            timestamp=intent.timestamp,
            salience=intent.salience,
            tags=intent.tags,
            metadata=intent.metadata,
        )
        chunk_written = self._jsonl_store.append_chunk(chunk)
        vector_written = False
        if intent.mode in {MemoryWriteMode.EVENT_ONLY, MemoryWriteMode.REVIEW_QUEUE, MemoryWriteMode.COMPATIBILITY_SNAPSHOT}:
            return MemoryWriteResult(accepted=True, chunk_written=chunk_written, notes=(intent.mode.value,))
        embedding = (await self._embeddings.embed_texts([chunk.text]))[0]
        await self._vector_store.upsert((VectorRecord(chunk=chunk, embedding=embedding),))
        vector_written = True
        return MemoryWriteResult(
            accepted=True,
            chunk_written=chunk_written,
            vector_written=vector_written,
            notes=(intent.mode.value,),
        )

