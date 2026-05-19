from __future__ import annotations

import json
from pathlib import Path

import xinyu_contextual_recall as contextual_recall
import xinyu_contextual_self_loop as contextual_self_loop
import xinyu_contextual_self_observatory as contextual_self_observatory
import xinyu_contextual_self_replay as contextual_self_replay
import xinyu_living_memory_recall as living_recall
from xinyu_contextual_recall import build_contextual_recall_prompt_block, build_contextual_recall_snapshot
from xinyu_contextual_self_loop import build_contextual_self_loop_snapshot


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_contextual_recall_modules_declare_non_owner_boundaries() -> None:
    assert contextual_recall.CANONICAL_RECALL_OWNER == living_recall.CANONICAL_RECALL_OWNER
    assert contextual_recall.CONTEXTUAL_RECALL_ROLE == "renderer/offline_context_pack"
    assert contextual_recall.CONTEXTUAL_RECALL_BOUNDARY == "not_canonical_living_memory_recall"
    assert contextual_self_loop.CANONICAL_RECALL_OWNER == living_recall.CANONICAL_RECALL_OWNER
    assert contextual_self_loop.CONTEXTUAL_SELF_LOOP_ROLE == "runtime_state_provider"
    assert contextual_self_loop.CONTEXTUAL_SELF_LOOP_BOUNDARY == "scene_and_pressure_provider_not_memory_recall_owner"
    assert contextual_self_observatory.CONTEXTUAL_SELF_OBSERVATORY_ROLE == "observability/no_behavior_change"
    assert contextual_self_replay.CONTEXTUAL_SELF_REPLAY_ROLE == "ops/lab_public_dataset_replay"


def test_contextual_recall_admits_memory_review_sources(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/contextual_self_loop_state.md",
        """
        - current_scene: memory_review
        - forgetting_posture: keep_indices_suppress_raw_history
        - retrieval_intents: memory_policy,context_horizon
        - working_self: careful_context_architect
        """,
    )
    _write(
        tmp_path / "memory/context/initiative_feedback_state.md",
        """
        - action: dismissed
        - future_effect: lower similar future initiative priority
        - scoring_bias_only: true
        """,
    )
    contextual_self = build_contextual_self_loop_snapshot(
        tmp_path,
        user_text="这些记忆应该怎么选择性遗忘和检索？",
        evaluated_at="2026-05-13T03:00:00+08:00",
    )

    snapshot = build_contextual_recall_snapshot(
        tmp_path,
        contextual_self=contextual_self,
        user_text="这些记忆应该怎么选择性遗忘和检索？",
        evaluated_at="2026-05-13T03:00:00+08:00",
    )

    assert snapshot.current_scene == "memory_review"
    assert len(snapshot.admitted) >= 2
    assert {item.source for item in snapshot.admitted} >= {"context_horizon", "initiative_feedback"}
    assert all(len(item.preview) <= 260 for item in snapshot.admitted)


def test_contextual_recall_prompt_writes_state_and_trace_without_raw_user_text(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/initiative_lifecycle_state.md",
        """
        - selected_decision: desktop_inbox
        - selected_score: 91
        - delivery_level: desktop_inbox
        - pending_feedback_count: 1
        """,
    )
    contextual_self = build_contextual_self_loop_snapshot(
        tmp_path,
        user_text="最近的主动反馈要怎么影响下一次打扰？",
        evaluated_at="2026-05-13T03:00:00+08:00",
    )

    block = build_contextual_recall_prompt_block(
        tmp_path,
        contextual_self=contextual_self,
        user_text="最近的主动反馈要怎么影响下一次打扰？",
        evaluated_at="2026-05-13T03:00:00+08:00",
    )
    state = (tmp_path / "memory/context/contextual_recall_state.md").read_text(encoding="utf-8")
    event = json.loads((tmp_path / "runtime/contextual_recall_trace.jsonl").read_text(encoding="utf-8").splitlines()[-1])

    assert "Contextual Recall Pack" in block
    assert "initiative_lifecycle" in block
    assert "admitted_recall_count: 1" in state
    assert event["admitted_recall_count"] == 1
    assert event["user_text_hash"]
    assert "最近的主动反馈" not in json.dumps(event, ensure_ascii=False)


def test_contextual_recall_expands_sources_for_high_retrieval_pressure(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/interaction_journal_state.md",
        """
        - last_topic: owner asked about a prior answer
        - last_user_summary: owner wanted evidence from the previous dialogue
        - last_reply_summary: reply should cite only compact evidence
        """,
    )
    _write(
        tmp_path / "memory/context/continuity_handoff_state.md",
        """
        - continuity_mode: active
        - open_loop_count: 1
        - self_thought_thread: sparse evidence thread
        """,
    )
    contextual_self = build_contextual_self_loop_snapshot(
        tmp_path,
        user_text="\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f",
        evaluated_at="2026-05-13T03:00:00+08:00",
    )

    snapshot = build_contextual_recall_snapshot(
        tmp_path,
        contextual_self=contextual_self,
        user_text="\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f",
        evaluated_at="2026-05-13T03:00:00+08:00",
    )
    block = build_contextual_recall_prompt_block(
        tmp_path,
        contextual_self=contextual_self,
        user_text="\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f",
        evaluated_at="2026-05-13T03:00:00+08:00",
    )

    assert contextual_self.current_scene == "casual_chat"
    assert contextual_self.retrieval_pressure == "high"
    assert snapshot.retrieval_pressure == "high"
    assert snapshot.evidence_sufficiency == "usable"
    assert snapshot.answer_discipline == "answer_from_recalled_evidence_without_overclaim"
    assert "evidence_sufficiency: usable" in block
    assert "answer_discipline: answer_from_recalled_evidence_without_overclaim" in block
    assert {item.source for item in snapshot.admitted} >= {"interaction_journal", "continuity"}


def test_contextual_recall_marks_high_pressure_without_evidence_as_none(tmp_path: Path) -> None:
    contextual_self = build_contextual_self_loop_snapshot(
        tmp_path,
        user_text="\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f",
        evaluated_at="2026-05-13T03:00:00+08:00",
    )

    snapshot = build_contextual_recall_snapshot(
        tmp_path,
        contextual_self=contextual_self,
        user_text="\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f",
        evaluated_at="2026-05-13T03:00:00+08:00",
    )

    assert contextual_self.retrieval_pressure == "high"
    assert snapshot.admitted == ()
    assert snapshot.evidence_sufficiency == "none"
    assert snapshot.answer_discipline == "answer_current_only_acknowledge_missing_evidence"
