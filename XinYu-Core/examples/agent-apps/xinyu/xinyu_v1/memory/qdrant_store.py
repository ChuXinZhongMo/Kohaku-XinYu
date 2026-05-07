"""Qdrant vector-store adapter.

The dependency is optional. Import and connection errors are surfaced as health
degradation instead of breaking the whole v1 runtime at import time.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import VectorStoreUnavailableError
from ..types import Embedding, HealthState, ServiceHealth
from .models import MemoryQuery, MemorySearchResult
from .vector_store import VectorRecord


@dataclass(slots=True)
class QdrantVectorStore:
    url: str
    collection_name: str
    api_key: str = ""
    vector_size: int = 1536

    def _client(self):
        try:
            from qdrant_client import QdrantClient  # type: ignore
        except ImportError as exc:
            raise VectorStoreUnavailableError("qdrant-client is not installed") from exc
        return QdrantClient(url=self.url, api_key=self.api_key or None)

    async def upsert(self, records: tuple[VectorRecord, ...]) -> None:
        if not records:
            return
        client = self._client()
        from qdrant_client.models import PointStruct  # type: ignore

        points = [
            PointStruct(id=record.chunk.chunk_id, vector=list(record.embedding), payload=record.chunk.to_json())
            for record in records
        ]
        client.upsert(collection_name=self.collection_name, points=points)

    async def search(self, query: MemoryQuery, embedding: Embedding) -> tuple[MemorySearchResult, ...]:
        client = self._client()
        hits = client.search(
            collection_name=self.collection_name,
            query_vector=list(embedding),
            limit=max(1, query.limit),
            with_payload=True,
        )
        from .jsonl_store import chunk_from_mapping

        results: list[MemorySearchResult] = []
        for hit in hits:
            payload = getattr(hit, "payload", {}) or {}
            chunk = chunk_from_mapping(payload)
            if chunk is None:
                continue
            score = float(getattr(hit, "score", 0.0))
            if score >= query.min_score:
                results.append(MemorySearchResult(chunk=chunk, score=score, reason="qdrant"))
        return tuple(results)

    async def delete(self, chunk_ids: tuple[str, ...]) -> None:
        if not chunk_ids:
            return
        client = self._client()
        client.delete(collection_name=self.collection_name, points_selector=list(chunk_ids))

    async def health(self) -> ServiceHealth:
        try:
            client = self._client()
            client.get_collection(self.collection_name)
        except Exception as exc:
            return ServiceHealth(component="qdrant", state=HealthState.DEGRADED, message=str(exc))
        return ServiceHealth(component="qdrant", state=HealthState.OK, details={"collection": self.collection_name})

