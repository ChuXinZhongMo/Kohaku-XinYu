"""Hybrid memory retrieval."""

from __future__ import annotations

from .embeddings import EmbeddingProvider, HashEmbeddingProvider
from .models import MemoryQuery, MemorySearchResult
from .vector_store import VectorStore


class MemoryRetriever:
    def __init__(self, vector_store: VectorStore, embeddings: EmbeddingProvider | None = None) -> None:
        self._vector_store = vector_store
        self._embeddings = embeddings or HashEmbeddingProvider()

    async def retrieve(self, query: MemoryQuery) -> tuple[MemorySearchResult, ...]:
        if not query.text.strip():
            return ()
        embedding = (await self._embeddings.embed_texts([query.text]))[0]
        results = await self._vector_store.search(query, embedding)
        return tuple(result for result in results if result.score >= query.min_score)

