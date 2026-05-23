from __future__ import annotations

from pathlib import Path

from xinyu_dialogue_archive import list_memory_candidates, store_memory_candidate, update_memory_candidate_status
from xinyu_memory_self_review import (
    OBSERVE_MORE_OWNER_PREFERENCE,
    OWNER_REVIEW_REQUIRED,
    run_memory_self_review,
)


def _store_candidate(
    root: Path,
    candidate_id: str,
    *,
    text: str,
    source_turn_id: str,
    source_message_ids: list[int],
    created_at: str,
) -> None:
    assert store_memory_candidate(
        root,
        candidate_id=candidate_id,
        candidate_type="owner_preference",
        source_message_ids=source_message_ids,
        source_turn_id=source_turn_id,
        candidate_text=f"owner preference candidate\nowner_turn: {text}",
        confidence_score=70,
        target_gate="owner_memory_review",
        target_memory_layer="memory/people/owner.md",
        reason="possible owner preference; review for repetition and stability",
        risk_flags=["memory_immune:observe_more", "scope:owner_private"],
        review_notes="pending review",
        created_at=created_at,
    )


def _ids_for_status(root: Path, status: str) -> set[str]:
    return {str(row.get("candidate_id")) for row in list_memory_candidates(root, status=status, limit=50)}


def test_memory_self_review_escalates_repeated_observed_preference(tmp_path: Path) -> None:
    _store_candidate(
        tmp_path,
        "pref-old",
        text="please remember I prefer concise replies",
        source_turn_id="turn-old",
        source_message_ids=[101],
        created_at="2026-05-20T12:00:00+08:00",
    )
    first = run_memory_self_review(tmp_path, checked_at="2026-05-20T12:01:00+08:00")
    _store_candidate(
        tmp_path,
        "pref-new",
        text="I prefer concise replies",
        source_turn_id="turn-new",
        source_message_ids=[102],
        created_at="2026-05-20T12:05:00+08:00",
    )

    second = run_memory_self_review(tmp_path, checked_at="2026-05-20T12:06:00+08:00")

    assert first["latest_decision"] == OBSERVE_MORE_OWNER_PREFERENCE
    assert _ids_for_status(tmp_path, OBSERVE_MORE_OWNER_PREFERENCE) == {"pref-old"}
    assert _ids_for_status(tmp_path, OWNER_REVIEW_REQUIRED) == {"pref-new"}
    decision = second["decisions"][0]
    assert decision["memory_review_recommendation"] == "repeated_evidence_ready_for_owner_review"
    assert decision["evidence_count"] == "2"
    assert decision["supporting_candidate_ids"] == "pref-old"
    assert "evidence_count=2" in decision["review_notes"]


def test_memory_self_review_routes_conflicting_preference_to_owner_review(tmp_path: Path) -> None:
    _store_candidate(
        tmp_path,
        "pref-positive",
        text="owner prefers concise replies",
        source_turn_id="turn-positive",
        source_message_ids=[201],
        created_at="2026-05-20T12:00:00+08:00",
    )
    assert update_memory_candidate_status(
        tmp_path,
        candidate_id="pref-positive",
        status=OBSERVE_MORE_OWNER_PREFERENCE,
        review_notes="observed previous owner preference",
    )
    _store_candidate(
        tmp_path,
        "pref-negative",
        text="owner does not prefer concise replies",
        source_turn_id="turn-negative",
        source_message_ids=[202],
        created_at="2026-05-20T12:05:00+08:00",
    )

    result = run_memory_self_review(tmp_path, checked_at="2026-05-20T12:06:00+08:00")

    assert _ids_for_status(tmp_path, OWNER_REVIEW_REQUIRED) == {"pref-negative"}
    assert result["owner_review_required"] == 1
    assert result["conflict_review_required"] == 1
    decision = result["decisions"][0]
    assert decision["risk"] == "conflict"
    assert decision["memory_review_recommendation"] == "hold_conflict_review"
    assert decision["conflict_count"] == "1"
    assert decision["conflicting_candidate_ids"] == "pref-positive"


def test_memory_self_review_routes_post_reply_growth_to_owner_review(tmp_path: Path) -> None:
    assert store_memory_candidate(
        tmp_path,
        candidate_id="growth-candidate",
        candidate_type="post_reply_growth_candidate",
        source_message_ids=[301],
        source_turn_id="turn-growth",
        candidate_text="post-reply growth candidate; raw owner/reply text intentionally omitted",
        confidence_score=76,
        target_gate="personality_growth_review",
        target_memory_layer="memory/reflection/growth_log.md",
        reason="repeated raw-text-safe post-reply observation success plus explicit owner positive feedback",
        risk_flags=["memory_immune:review", "scope:owner_private"],
        created_at="2026-05-20T12:10:00+08:00",
    )

    result = run_memory_self_review(tmp_path, checked_at="2026-05-20T12:11:00+08:00")

    assert _ids_for_status(tmp_path, OWNER_REVIEW_REQUIRED) == {"growth-candidate"}
    decision = result["decisions"][0]
    assert decision["candidate_type"] == "post_reply_growth_candidate"
    assert decision["action"] == "ask_owner_to_confirm_growth_log_draft"
    assert "never rewrite stable personality" in decision["rationale"]
