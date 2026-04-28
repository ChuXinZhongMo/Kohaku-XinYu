"""Legacy memory migration utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..types import JSONValue
from .embeddings import EmbeddingProvider, HashEmbeddingProvider
from .markdown_legacy import LegacyMarkdownMemory
from .models import MemoryChunk
from .vector_store import VectorRecord, VectorStore


@dataclass(frozen=True, slots=True)
class MigrationReport:
    dry_run: bool
    chunks_seen: int
    chunks_upserted: int
    notes: tuple[str, ...]

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "dry_run": self.dry_run,
            "chunks_seen": self.chunks_seen,
            "chunks_upserted": self.chunks_upserted,
            "notes": list(self.notes),
        }


async def migrate_markdown_memory(
    *,
    memory_root: Path,
    vector_store: VectorStore,
    embeddings: EmbeddingProvider | None = None,
    dry_run: bool = True,
) -> MigrationReport:
    legacy = LegacyMarkdownMemory(memory_root)
    provider = embeddings or HashEmbeddingProvider()
    chunks = legacy.iter_chunks()
    if dry_run or not chunks:
        return MigrationReport(dry_run=dry_run, chunks_seen=len(chunks), chunks_upserted=0, notes=("legacy_md_scan",))

    vectors = await provider.embed_texts([chunk.text for chunk in chunks])
    records = tuple(VectorRecord(chunk=chunk, embedding=embedding) for chunk, embedding in zip(chunks, vectors, strict=True))
    await vector_store.upsert(records)
    return MigrationReport(
        dry_run=False,
        chunks_seen=len(chunks),
        chunks_upserted=len(records),
        notes=("legacy_md_upsert",),
    )


def chunk_manifest(chunks: tuple[MemoryChunk, ...]) -> list[dict[str, JSONValue]]:
    return [
        {
            "chunk_id": chunk.chunk_id,
            "layer": chunk.layer.value,
            "source_path": chunk.source_path,
            "text_length": len(chunk.text),
        }
        for chunk in chunks
    ]

