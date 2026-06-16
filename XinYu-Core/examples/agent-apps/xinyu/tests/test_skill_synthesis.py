from __future__ import annotations

from pathlib import Path

from xinyu_dialogue_archive import store_memory_candidate, update_memory_candidate_status
from xinyu_skill_library import list_skills
from xinyu_skill_synthesis import run_skill_synthesis


def _seed_candidate(root: Path, candidate_id: str, text: str, *, ctype: str = "owner_preference", status: str = "owner_review_required") -> None:
    store_memory_candidate(
        root,
        candidate_id=candidate_id,
        candidate_type=ctype,
        source_message_ids=[1],
        source_turn_id=f"turn-{candidate_id}",
        candidate_text=text,
        confidence_score=70,
        target_gate="owner_preference_gate",
        target_memory_layer="memory/people/owner.md",
        reason="owner stated a durable preference",
    )
    update_memory_candidate_status(root, candidate_id=candidate_id, status=status)


def test_corroborated_candidates_produce_a_skill(tmp_path: Path) -> None:
    # the same claim repeated across turns -> same topic key -> corroborated -> skill
    claim = "owner_turn: 我喜欢简洁直接的回答方式"
    _seed_candidate(tmp_path, "c1", claim)
    _seed_candidate(tmp_path, "c2", claim)

    result = run_skill_synthesis(tmp_path, min_evidence=2)
    assert result["created"] >= 1
    skills = list_skills(tmp_path)
    assert skills
    assert any(s["tags"] == ["owner_preference"] for s in skills)


def test_single_candidate_does_not_produce_skill(tmp_path: Path) -> None:
    _seed_candidate(tmp_path, "solo", "owner_turn: 一次性的随口偏好")
    result = run_skill_synthesis(tmp_path, min_evidence=2)
    assert result["created"] == 0
    assert list_skills(tmp_path) == []


def test_rerun_updates_not_duplicates(tmp_path: Path) -> None:
    claim = "owner_turn: 我喜欢简洁直接的回答方式"
    _seed_candidate(tmp_path, "c1", claim)
    _seed_candidate(tmp_path, "c2", claim)
    run_skill_synthesis(tmp_path, min_evidence=2)
    count_after_first = len(list_skills(tmp_path))
    second = run_skill_synthesis(tmp_path, min_evidence=2)
    assert second["created"] == 0
    assert second["updated"] >= 1
    assert len(list_skills(tmp_path)) == count_after_first
