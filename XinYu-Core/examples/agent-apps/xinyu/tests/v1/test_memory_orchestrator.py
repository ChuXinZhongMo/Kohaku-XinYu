from __future__ import annotations

from xinyu_v1.memory.models import MemoryEvent, MemoryQuery, MemoryWriteIntent
from xinyu_v1.memory.orchestrator import MemoryOrchestrator
from xinyu_v1.types import MemoryLayer, MemoryWriteMode, PrivacyScope, SourceChannel, TraceContext


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


async def test_memory_rehydrates_persisted_stable_chunks(tmp_path) -> None:
    first = MemoryOrchestrator(runtime_root=tmp_path)
    await first.write(
        MemoryWriteIntent(
            text="owner likes quiet short replies",
            layer=MemoryLayer.CONTEXT,
            mode=MemoryWriteMode.STABLE_ALLOWED,
            timestamp="2026-01-01T00:00:00+00:00",
            tags=("owner",),
        )
    )

    fresh = MemoryOrchestrator(runtime_root=tmp_path)
    matches = await fresh.retrieve(MemoryQuery(text="quiet replies", limit=3))

    assert matches
    assert matches[0].chunk.layer is MemoryLayer.CONTEXT


async def test_cjk_phrase_recall_uses_character_ngrams(tmp_path) -> None:
    orchestrator = MemoryOrchestrator(runtime_root=tmp_path)
    await orchestrator.write(
        MemoryWriteIntent(
            text="\u70e4\u8089\u996d\u9002\u5408\u914d\u51b0\u6c34",
            layer=MemoryLayer.CONTEXT,
            mode=MemoryWriteMode.STABLE_ALLOWED,
            timestamp="2026-01-01T00:00:00+00:00",
            tags=("owner",),
        )
    )

    matches = await orchestrator.retrieve(MemoryQuery(text="\u51b0\u6c34", limit=3, min_score=0.01))

    assert matches
    assert "\u51b0\u6c34" in matches[0].chunk.text


async def test_recent_messages_are_session_scoped_and_exclude_current_trace(tmp_path) -> None:
    orchestrator = MemoryOrchestrator(runtime_root=tmp_path)
    await orchestrator.record_event(
        MemoryEvent.from_text(
            text="previous user line",
            timestamp="2026-01-01T00:00:00+00:00",
            source_channel=SourceChannel.QQ_PRIVATE,
            privacy_scope=PrivacyScope.EXTERNAL_PRIVATE,
            actor_hash="actor",
            metadata={"role": "user", "session_hash": "session-a", "trace_id": "tr-1"},
        )
    )
    await orchestrator.record_event(
        MemoryEvent.from_text(
            text="previous assistant line with iced water",
            timestamp="2026-01-01T00:00:01+00:00",
            source_channel=SourceChannel.SYSTEM,
            privacy_scope=PrivacyScope.EXTERNAL_PRIVATE,
            actor_hash="actor",
            metadata={"role": "assistant", "session_hash": "session-a", "trace_id": "tr-1"},
        )
    )
    await orchestrator.record_event(
        MemoryEvent.from_text(
            text="current user line",
            timestamp="2026-01-01T00:00:02+00:00",
            source_channel=SourceChannel.QQ_PRIVATE,
            privacy_scope=PrivacyScope.EXTERNAL_PRIVATE,
            actor_hash="actor",
            metadata={"role": "user", "session_hash": "session-a", "trace_id": "tr-2"},
        )
    )
    await orchestrator.record_event(
        MemoryEvent.from_text(
            text="other session line",
            timestamp="2026-01-01T00:00:03+00:00",
            source_channel=SourceChannel.QQ_PRIVATE,
            privacy_scope=PrivacyScope.EXTERNAL_PRIVATE,
            actor_hash="actor",
            metadata={"role": "user", "session_hash": "session-b", "trace_id": "tr-x"},
        )
    )

    messages = await orchestrator.recent_messages(
        TraceContext(trace_id="tr-2", session_hash="session-a"),
        exclude_trace_ids=("tr-2",),
    )

    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[-1].text == "previous assistant line with iced water"
    assert all("current user line" not in message.text for message in messages)
    assert all("other session line" not in message.text for message in messages)


async def test_retrieve_honors_source_and_privacy_filters(tmp_path) -> None:
    orchestrator = MemoryOrchestrator(runtime_root=tmp_path)
    await orchestrator.write(
        MemoryWriteIntent(
            text="shared keyword owner private detail",
            layer=MemoryLayer.CONTEXT,
            mode=MemoryWriteMode.STABLE_ALLOWED,
            timestamp="2026-01-01T00:00:00+00:00",
            metadata={
                "source_channel": SourceChannel.OWNER_PRIVATE.value,
                "privacy_scope": PrivacyScope.OWNER_PRIVATE.value,
            },
        )
    )
    await orchestrator.write(
        MemoryWriteIntent(
            text="shared keyword group detail",
            layer=MemoryLayer.CONTEXT,
            mode=MemoryWriteMode.STABLE_ALLOWED,
            timestamp="2026-01-01T00:00:01+00:00",
            metadata={
                "source_channel": SourceChannel.QQ_GROUP.value,
                "privacy_scope": PrivacyScope.GROUP_CONTEXT.value,
            },
        )
    )

    matches = await orchestrator.retrieve(
        MemoryQuery(
            text="shared keyword detail",
            source_channels=(SourceChannel.OWNER_PRIVATE,),
            privacy_scopes=(PrivacyScope.OWNER_PRIVATE,),
            limit=5,
        )
    )

    assert len(matches) == 1
    assert "owner private" in matches[0].chunk.text
