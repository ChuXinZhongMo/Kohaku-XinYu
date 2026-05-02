"""High-level memory API for v1 runtime layers."""

from __future__ import annotations

from pathlib import Path

from ..types import HealthState, MemoryLayer, MemoryWriteMode, ServiceHealth, SourceChannel, TraceContext
from .embeddings import EmbeddingProvider, HashEmbeddingProvider
from .jsonl_store import JsonlMemoryStore
from .models import ConversationMessage, MemoryEvent, MemoryQuery, MemorySearchResult, MemoryWriteIntent
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
        self._bootstrapped_from_jsonl = False

    async def bootstrap_from_chunks(self, chunks: tuple[VectorRecord, ...]) -> None:
        await self._vector_store.upsert(chunks)
        self._bootstrapped_from_jsonl = True

    async def record_event(self, event: MemoryEvent) -> MemoryWriteResult:
        return await self._writer.write_event(event)

    async def write(self, intent: MemoryWriteIntent) -> MemoryWriteResult:
        if intent.mode is MemoryWriteMode.NONE:
            return MemoryWriteResult(accepted=False, notes=("write_mode_none",))
        return await self._writer.write_intent(intent)

    async def retrieve(self, query: MemoryQuery) -> tuple[MemorySearchResult, ...]:
        await self._ensure_bootstrapped_from_jsonl()
        return await self._retriever.retrieve(query)

    async def recent_messages(
        self,
        trace: TraceContext | None,
        *,
        limit: int = 8,
        exclude_trace_ids: tuple[str, ...] = (),
    ) -> tuple[ConversationMessage, ...]:
        safe_limit = max(0, limit)
        if safe_limit == 0 or trace is None or not trace.session_hash:
            return ()
        excluded = {item for item in exclude_trace_ids if item}
        messages: list[ConversationMessage] = []
        for event in self._jsonl_store.load_events():
            metadata = event.metadata
            if str(metadata.get("session_hash") or "") != trace.session_hash:
                continue
            trace_id = str(metadata.get("trace_id") or "")
            if trace_id and trace_id in excluded:
                continue
            role = _conversation_role(event)
            if not role:
                continue
            text = event.text.strip()
            if not text:
                continue
            messages.append(
                ConversationMessage(
                    role=role,
                    text=text,
                    timestamp=event.timestamp,
                    event_id=event.event_id,
                    trace_id=trace_id,
                    source_channel=event.source_channel,
                    privacy_scope=event.privacy_scope,
                )
            )
        return tuple(messages[-safe_limit:])

    async def health(self) -> ServiceHealth:
        try:
            return await self._vector_store.health()
        except Exception as exc:
            return ServiceHealth(component="memory_orchestrator", state=HealthState.DEGRADED, message=str(exc))

    async def _ensure_bootstrapped_from_jsonl(self) -> None:
        if self._bootstrapped_from_jsonl:
            return
        chunks = tuple(chunk for chunk in self._jsonl_store.load_chunks() if chunk.layer is not MemoryLayer.EVENTS)
        if chunks:
            embeddings = await self._embeddings.embed_texts([chunk.text for chunk in chunks])
            await self._vector_store.upsert(
                tuple(VectorRecord(chunk=chunk, embedding=embedding) for chunk, embedding in zip(chunks, embeddings))
            )
        self._bootstrapped_from_jsonl = True


def _conversation_role(event: MemoryEvent) -> str:
    role = str(event.metadata.get("role") or "").strip().lower()
    if role in {"user", "assistant"}:
        return role
    if event.source_channel is SourceChannel.SYSTEM:
        return "assistant"
    return "user"
