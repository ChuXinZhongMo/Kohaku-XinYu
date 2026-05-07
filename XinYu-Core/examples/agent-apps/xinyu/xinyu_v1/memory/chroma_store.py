"""Chroma vector-store adapter."""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import VectorStoreUnavailableError
from ..types import Embedding, HealthState, ServiceHealth
from .models import MemoryQuery, MemorySearchResult
from .vector_store import VectorRecord


@dataclass(slots=True)
class ChromaVectorStore:
    persist_path: str
    collection_name: str

    def _collection(self):
        try:
            import chromadb  # type: ignore
        except ImportError as exc:
            raise VectorStoreUnavailableError("chromadb is not installed") from exc
        client = chromadb.PersistentClient(path=self.persist_path)
        return client.get_or_create_collection(self.collection_name)

    async def upsert(self, records: tuple[VectorRecord, ...]) -> None:
        if not records:
            return
        collection = self._collection()
        collection.upsert(
            ids=[record.chunk.chunk_id for record in records],
            embeddings=[list(record.embedding) for record in records],
            documents=[record.chunk.text for record in records],
            metadatas=[record.chunk.to_json() for record in records],
        )

    async def search(self, query: MemoryQuery, embedding: Embedding) -> tuple[MemorySearchResult, ...]:
        collection = self._collection()
        response = collection.query(query_embeddings=[list(embedding)], n_results=max(1, query.limit))
        metadatas = (response.get("metadatas") or [[]])[0]
        distances = (response.get("distances") or [[]])[0]
        from .jsonl_store import chunk_from_mapping

        results: list[MemorySearchResult] = []
        for metadata, distance in zip(metadatas, distances, strict=False):
            chunk = chunk_from_mapping(metadata or {})
            if chunk is None:
                continue
            score = max(0.0, 1.0 - float(distance))
            if score >= query.min_score:
                results.append(MemorySearchResult(chunk=chunk, score=score, reason="chroma"))
        return tuple(results)

    async def delete(self, chunk_ids: tuple[str, ...]) -> None:
        if chunk_ids:
            self._collection().delete(ids=list(chunk_ids))

    async def health(self) -> ServiceHealth:
        try:
            collection = self._collection()
            count = collection.count()
        except Exception as exc:
            return ServiceHealth(component="chroma", state=HealthState.DEGRADED, message=str(exc))
        return ServiceHealth(component="chroma", state=HealthState.OK, details={"records": count})

