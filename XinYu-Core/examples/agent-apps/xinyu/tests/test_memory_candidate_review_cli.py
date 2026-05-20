from __future__ import annotations

from xinyu_dialogue_archive import list_memory_candidates, store_memory_candidate
from xinyu_memory_candidate_review_cli import decide_candidate, explain_candidate, list_candidates, show_candidate


def _store(root, candidate_id: str, *, candidate_type: str = "project_fact", risk_flags: list[str] | None = None) -> None:
    assert store_memory_candidate(
        root,
        candidate_id=candidate_id,
        candidate_type=candidate_type,
        source_message_ids=[1, 2],
        source_turn_id="turn-source",
        candidate_text="project fact candidate",
        confidence_score=80,
        target_gate="owner_memory_review",
        target_memory_layer="candidate_memory",
        reason="extraction reason",
        risk_flags=risk_flags or ["memory_immune:review", "scope:owner_private"],
        review_notes="pending review",
        created_at="2026-05-20T12:00:00+08:00",
    )


def test_memory_candidate_provenance_is_stored_and_explained(tmp_path) -> None:
    _store(tmp_path, "memcand-provenance")

    row = list_memory_candidates(tmp_path, status="pending", limit=1)[0]
    explanation = explain_candidate(tmp_path, "memcand-provenance")

    assert row["source_turn_id"] == "turn-source"
    assert row["source_message_ids"] == [1, 2]
    assert row["risk_flags"] == ["memory_immune:review", "scope:owner_private"]
    assert explanation["ok"] is True
    assert explanation["source_turn_id"] == "turn-source"
    assert explanation["extraction_reason"] == "extraction reason"
    assert explanation["stable_memory_write"] == "blocked_until_review"


def test_memory_candidate_review_cli_lists_shows_and_rejects(tmp_path) -> None:
    _store(tmp_path, "memcand-review")

    listed = list_candidates(tmp_path, status="pending")
    shown = show_candidate(tmp_path, "memcand-review")
    rejected = decide_candidate(tmp_path, "memcand-review", decision="reject", review_notes="not stable")

    assert listed["count"] == 1
    assert shown["candidate"]["candidate_id"] == "memcand-review"
    assert rejected == {
        "ok": True,
        "candidate_id": "memcand-review",
        "status": "rejected",
        "review_notes": "not stable",
    }


def test_runtime_trace_or_timeout_candidate_cannot_be_approved_directly(tmp_path) -> None:
    _store(
        tmp_path,
        "memcand-timeout",
        risk_flags=["runtime_trace", "timeout", "temporary_operational"],
    )

    result = decide_candidate(tmp_path, "memcand-timeout", decision="approve", review_notes="looks useful")

    assert result["ok"] is False
    assert result["error"] == "runtime_or_timeout_candidate_cannot_be_approved_directly"


def test_high_risk_relationship_candidate_requires_explicit_owner_approval(tmp_path) -> None:
    _store(tmp_path, "memcand-relationship", candidate_type="relationship_signal")

    blocked = decide_candidate(tmp_path, "memcand-relationship", decision="approve", review_notes="approve")
    approved = decide_candidate(
        tmp_path,
        "memcand-relationship",
        decision="approve",
        review_notes="owner_approved_high_risk after review",
    )

    assert blocked["ok"] is False
    assert blocked["error"] == "high_risk_candidate_requires_explicit_owner_approval"
    assert approved["ok"] is True
    assert approved["status"] == "approved"
