from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_dialogue_archive import list_memory_candidates  # noqa: E402
from xinyu_memory_candidate_extractor import extract_memory_candidates  # noqa: E402
from xinyu_runtime_context import build_renderer_memory_context  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def test_runtime_context_includes_turn_triage_for_short_continue(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/recent_context.md",
        "Batch C plan exists with next implementation step and worklog recovery point.",
    )

    context = build_renderer_memory_context(tmp_path, user_text="\u7ee7\u7eed")

    assert "[runtime/turn_triage_gate]" in context
    assert "- primary_lane: active_task_continue" in context
    assert "- current_task_policy: resume_without_reasking" in context


def test_runtime_context_includes_slow_state_for_low_energy_scene(tmp_path: Path) -> None:
    context = build_renderer_memory_context(
        tmp_path,
        user_text="\u6211\u521a\u4e0b\u5b8c\u591c\u73ed\u6709\u70b9\u56f0",
    )

    assert "[runtime/scene_frame]" in context
    assert "[runtime/slow_state_modulator]" in context
    assert "- reply_policy: low_burden_short" in context
    assert "- initiative_policy: suppress_optional_proactive" in context


def test_memory_candidate_extractor_records_immune_gate_notes(tmp_path: Path) -> None:
    payload = {
        "message_type": "private_text",
        "session_id": "s",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    result = extract_memory_candidates(
        tmp_path,
        payload,
        user_text="Codex runtime bridge test passed",
        assistant_reply="queued",
        source_message_ids=[1],
    )
    candidates = list_memory_candidates(tmp_path)

    assert result["candidate_count"] >= 1
    assert any("memory_immune:" in note for note in result["notes"])
    assert candidates
    assert "memory_immune=" in candidates[0]["review_notes"]
    assert "stable_write_allowed=false" in candidates[0]["review_notes"]


def test_memory_candidate_extractor_blocks_sensitive_immune_candidate(tmp_path: Path) -> None:
    payload = {
        "message_type": "private_text",
        "session_id": "s",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }

    result = extract_memory_candidates(
        tmp_path,
        payload,
        user_text="Codex runtime Authorization: Bearer secretsecretsecret123",
        assistant_reply="queued",
        source_message_ids=[1],
    )

    assert result["candidate_count"] == 0
    assert "memory_immune_blocked:" in " ".join(result["notes"])
    assert list_memory_candidates(tmp_path) == []
