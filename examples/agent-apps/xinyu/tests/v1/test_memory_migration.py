from __future__ import annotations

from xinyu_v1.memory.migration import migrate_markdown_memory
from xinyu_v1.memory.vector_store import InMemoryVectorStore


async def test_markdown_migration_dry_run_counts_chunks(tmp_path) -> None:
    memory_root = tmp_path / "memory"
    (memory_root / "context").mkdir(parents=True)
    (memory_root / "context" / "recent_context.md").write_text("one\n\n" + "two" * 100, encoding="utf-8")

    report = await migrate_markdown_memory(
        memory_root=memory_root,
        vector_store=InMemoryVectorStore(),
        dry_run=True,
    )

    assert report.dry_run is True
    assert report.chunks_seen >= 1
    assert report.chunks_upserted == 0

