from __future__ import annotations

from types import SimpleNamespace

from xinyu_living_memory_recall import RecalledContextItem
from xinyu_retrieval_need_reranker import (
    build_retrieval_need_profile,
    rerank_recalled_items,
    rerank_recalled_items_with_report,
)


def _item(
    source: str,
    summary: str,
    *,
    score: float,
    relevance: str = "test",
    confidence: str = "medium",
) -> RecalledContextItem:
    return RecalledContextItem(
        recall_id=f"test-{source}",
        source=source,
        scope="owner_private",
        time="test",
        speaker="memory",
        summary=summary,
        relevance=relevance,
        confidence=confidence,
        score=score,
    )


def test_direct_recall_prioritizes_dialogue_tail() -> None:
    profile = build_retrieval_need_profile(
        query_text="\u521a\u624d\u6211\u8bf4\u7684\u996e\u6599\u662f\u4ec0\u4e48",
        query_terms=("\u521a\u624d", "\u996e\u6599"),
        direct_recall=True,
    )
    ranked = rerank_recalled_items(
        [
            _item("stable_memory", "owner likes project status updates", score=5.0, confidence="high"),
            _item("dialogue_tail", "\u521a\u624d\u8bf4\u7684\u996e\u6599\u662f\u51b0\u6c34", score=2.0),
        ],
        profile,
    )

    assert ranked[0].source == "dialogue_tail"


def test_technical_status_prioritizes_stable_project_memory() -> None:
    profile = build_retrieval_need_profile(
        query_text="Codex runtime progress status",
        query_terms=("Codex", "runtime", "progress"),
        visible_turn=SimpleNamespace(technical_work=True),
    )
    ranked = rerank_recalled_items(
        [
            _item("dialogue_archive", "old Codex chat aside", score=4.0),
            _item("stable_memory", "runtime status and Codex bridge progress state", score=3.0),
        ],
        profile,
    )

    assert ranked[0].source == "stable_memory"


def test_self_core_topic_prioritizes_architecture_context() -> None:
    profile = build_retrieval_need_profile(
        query_text="API local tiny self core memory continuity",
        query_terms=("API", "self", "core"),
        self_core_topic=True,
    )
    ranked = rerank_recalled_items(
        [
            _item("dialogue_archive", "API discussion from an old chat", score=8.0, confidence="high"),
            _item(
                "self_core_architecture_context",
                "local tiny self core is an architecture note, not stable personality memory",
                score=4.0,
            ),
        ],
        profile,
    )

    assert ranked[0].source == "self_core_architecture_context"


def test_rerank_report_exposes_flags_without_raw_query() -> None:
    profile = build_retrieval_need_profile(
        query_text="\u521a\u624d Codex runtime \u8fdb\u5ea6",
        query_terms=("Codex", "runtime", "\u8fdb\u5ea6"),
        direct_recall=True,
    )
    report = rerank_recalled_items_with_report(
        [
            _item("dialogue_archive", "Codex runtime archive", score=3.0),
            _item("stable_memory", "runtime progress memory", score=4.0),
        ],
        profile,
        limit=1,
    )

    assert report.items[0].source in {"dialogue_archive", "stable_memory"}
    assert report.decisions
    assert report.envelopes
    assert report.decisions[0].selected is True
    assert report.envelopes[0].selected is True
    assert report.envelopes[0].boundary
    assert "direct_recall" in report.profile_flags
    assert "technical_work" in report.profile_flags
    notes = report.note_lines()
    assert "need_aware_rerank_v1" in notes
    assert "candidate_envelope_v1" in notes
    assert not any("\u521a\u624d Codex runtime \u8fdb\u5ea6" in note for note in notes)
