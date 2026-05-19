from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import xinyu_living_memory_recall as living_recall
from xinyu_living_memory_recall import (
    LivingMemoryRecall,
    RecalledContextItem,
    RecalledContextResult,
    run_living_memory_recall_algorithm,
)


def test_living_memory_recall_declares_canonical_owner_and_provider_boundary() -> None:
    import xinyu_context_retrieval as context_provider

    assert (
        living_recall.CANONICAL_RECALL_OWNER
        == "xinyu_living_memory_recall.run_living_memory_recall_algorithm"
    )
    assert living_recall.CANONICAL_RECALL_RESULT_SHAPE == "xinyu_context_retrieval.RecalledContextResult"
    assert living_recall.LEGACY_RECALL_PROVIDER == "xinyu_context_retrieval.retrieve_recalled_context"
    assert "xinyu_context_retrieval" in living_recall.RECALL_PROVIDER_MODULES
    assert context_provider.CANONICAL_RECALL_OWNER == living_recall.CANONICAL_RECALL_OWNER
    assert context_provider.CONTEXT_RETRIEVAL_ROLE == "provider/compatibility"
    assert living_recall.retrieve_recalled_context is living_recall.retrieve_living_memory


def test_living_memory_recall_delegates_to_current_engine(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def fake_retrieve(
        root: Path,
        payload: dict[str, Any] | None,
        *,
        user_text: str,
        dialogue_tail: list[dict[str, str]] | None = None,
        visible_turn: Any | None = None,
    ) -> RecalledContextResult:
        captured.update(
            {
                "root": root,
                "payload": payload,
                "user_text": user_text,
                "dialogue_tail": dialogue_tail,
                "visible_turn": visible_turn,
            }
        )
        return RecalledContextResult(
            turn_id="turn-test",
            query_text=user_text,
            prompt_block="",
            items=(),
            notes=("living_memory_owner",),
        )

    monkeypatch.setattr(living_recall, "_retrieve_recalled_context", fake_retrieve)

    visible_turn = object()
    dialogue_tail = [{"role": "user", "content": "上一句"}]
    result = LivingMemoryRecall(tmp_path).retrieve(
        {"message_type": "private"},
        user_text="继续刚才的话题",
        dialogue_tail=dialogue_tail,
        visible_turn=visible_turn,
    )

    assert result.notes == ("living_memory_owner",)
    assert captured == {
        "root": tmp_path,
        "payload": {"message_type": "private"},
        "user_text": "继续刚才的话题",
        "dialogue_tail": dialogue_tail,
        "visible_turn": visible_turn,
    }


def test_memory_write_signal_contract_is_small_and_explicit() -> None:
    signals = living_recall.LONG_LIVED_MEMORY_WRITE_SIGNALS

    assert "prediction_error" in signals
    assert "owner_approved_summary" in signals
    assert len(signals) <= 12


def test_living_memory_recall_algorithm_is_single_entry(monkeypatch, tmp_path: Path) -> None:
    item = RecalledContextItem(
        recall_id="tail-1",
        source="dialogue_tail",
        scope="owner_private",
        time="now",
        speaker="owner",
        summary="owner just said they are tired",
        relevance="current turn",
        confidence="high",
        score=9.0,
    )

    def fake_retrieve(
        root: Path,
        payload: dict[str, Any] | None,
        *,
        user_text: str,
        dialogue_tail: list[dict[str, str]] | None = None,
        visible_turn: Any | None = None,
    ) -> RecalledContextResult:
        return RecalledContextResult(
            turn_id="turn-test",
            query_text=user_text,
            prompt_block="## Recalled Context",
            items=(item,),
            notes=("recalled_context_active",),
        )

    monkeypatch.setattr(living_recall, "_retrieve_recalled_context", fake_retrieve)

    run = run_living_memory_recall_algorithm(
        tmp_path,
        {"message_type": "private"},
        user_text="刚才我说我困了",
        dialogue_tail=[],
    )

    assert run.result.items[0].recall_id == item.recall_id
    assert run.buckets.must_remember[0].recall_id == item.recall_id
    assert "## Recalled Context" in run.prompt_block
    assert "## Temporal Context" in run.prompt_block
    assert run.notes[0] == "living_memory_recall_algorithm_v1"
    assert "neuro_rules:hippocampal_index_not_dump,goal_gated_retrieval,temporal_context_binding" in run.notes


def test_compatibility_retrieve_uses_single_algorithm(monkeypatch, tmp_path: Path) -> None:
    expected = RecalledContextResult(
        turn_id="turn-compat",
        query_text="compat",
        prompt_block="",
        items=(),
        notes=("from_single_algorithm",),
    )
    captured: dict[str, Any] = {}

    def fake_run(
        root: Path,
        payload: dict[str, Any] | None,
        *,
        user_text: str,
        dialogue_tail: list[dict[str, str]] | None = None,
        visible_turn: Any | None = None,
        evaluated_at: str | None = None,
        log: bool = False,
    ) -> SimpleNamespace:
        captured.update(
            {
                "root": root,
                "payload": payload,
                "user_text": user_text,
                "dialogue_tail": dialogue_tail,
                "visible_turn": visible_turn,
                "evaluated_at": evaluated_at,
                "log": log,
            }
        )
        return SimpleNamespace(result=expected)

    monkeypatch.setattr(living_recall, "run_living_memory_recall_algorithm", fake_run)

    visible_turn = object()
    dialogue_tail = [{"role": "user", "content": "tail"}]
    actual = living_recall.retrieve_living_memory(
        tmp_path,
        {"message_type": "private"},
        user_text="current",
        dialogue_tail=dialogue_tail,
        visible_turn=visible_turn,
    )

    assert actual is expected
    assert captured == {
        "root": tmp_path,
        "payload": {"message_type": "private"},
        "user_text": "current",
        "dialogue_tail": dialogue_tail,
        "visible_turn": visible_turn,
        "evaluated_at": None,
        "log": False,
    }


def test_living_memory_recall_buckets_public_result_shape(tmp_path: Path) -> None:
    tail = RecalledContextItem(
        recall_id="tail-1",
        source="dialogue_tail",
        scope="owner_private",
        time="now",
        speaker="owner",
        summary="owner just said they are tired",
        relevance="current turn",
        confidence="high",
        score=9.0,
    )
    archive = RecalledContextItem(
        recall_id="archive-1",
        source="dialogue_archive",
        scope="owner_private",
        time="past",
        speaker="owner",
        summary="similar older pressure",
        relevance="pattern",
        confidence="medium",
        score=4.0,
    )
    result = RecalledContextResult(
        turn_id="turn-test",
        query_text="困",
        prompt_block="",
        items=(archive, tail),
        notes=("correction_possible",),
    )

    buckets = LivingMemoryRecall(tmp_path).bucket(result)

    assert buckets.must_remember == (tail,)
    assert buckets.experience_hints == (archive,)
    assert buckets.uncertainties == ("correction_possible",)
    assert buckets.trace == ("dialogue_archive:4.0", "dialogue_tail:9.0")


def test_living_memory_recall_adds_temporal_context_after_keyword_recall(monkeypatch, tmp_path: Path) -> None:
    sleep_start = RecalledContextItem(
        recall_id="archive-nap-start",
        source="dialogue_archive",
        scope="owner_private",
        time="2026.5.18 12:30",
        speaker="owner",
        summary="owner said they would take a nap",
        relevance="archive match",
        confidence="medium",
        score=5.0,
    )
    sleep_end = RecalledContextItem(
        recall_id="archive-nap-end",
        source="dialogue_archive",
        scope="owner_private",
        time="2026.5.18 13:30",
        speaker="owner",
        summary="owner woke up from the nap",
        relevance="archive match",
        confidence="medium",
        score=5.2,
    )

    def fake_retrieve(
        root: Path,
        payload: dict[str, Any] | None,
        *,
        user_text: str,
        dialogue_tail: list[dict[str, str]] | None = None,
        visible_turn: Any | None = None,
    ) -> RecalledContextResult:
        return RecalledContextResult(
            turn_id="turn-nap",
            query_text=user_text,
            prompt_block="## Recalled Context",
            items=(sleep_end, sleep_start),
            notes=("recalled_context_active",),
        )

    monkeypatch.setattr(living_recall, "_retrieve_recalled_context", fake_retrieve)

    run = run_living_memory_recall_algorithm(
        tmp_path,
        {"message_type": "private"},
        user_text="\u6211\u9192\u4e86",
        evaluated_at="2026-05-18T13:35:00+08:00",
    )

    assert "temporal_memory_context_v1" in run.result.notes
    assert "temporal_inference:recent_wake_from_nap" in run.result.notes
    assert "## Temporal Context" in run.prompt_block
    assert "inference: recent_wake_from_nap" in run.prompt_block
    assert all("time_context:" in item.relevance for item in run.result.items)
