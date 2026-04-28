from __future__ import annotations

from xinyu_v1.memory.models import MemoryQuery, MemoryWriteIntent
from xinyu_v1.memory.orchestrator import MemoryOrchestrator
from xinyu_v1.types import MemoryLayer, MemoryWriteMode


async def test_memory_write_and_retrieve(tmp_path) -> None:
    orchestrator = MemoryOrchestrator(runtime_root=tmp_path)
    result = await orchestrator.write(
        MemoryWriteIntent(
            text="owner likes quiet short replies",
            layer=MemoryLayer.CONTEXT,
            mode=MemoryWriteMode.STABLE_ALLOWED,
            timestamp="2026-01-01T00:00:00+00:00",
            tags=("owner",),
        )
    )
    assert result.accepted
    matches = await orchestrator.retrieve(MemoryQuery(text="quiet replies", limit=3))
    assert matches
    assert matches[0].chunk.layer is MemoryLayer.CONTEXT

