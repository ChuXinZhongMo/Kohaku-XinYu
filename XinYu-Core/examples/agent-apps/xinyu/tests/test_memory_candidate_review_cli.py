from __future__ import annotations

from typing import Any

from xinyu_dialogue_archive import list_memory_candidates, store_memory_candidate
from xinyu_memory_candidate_review_cli import decide_candidate, explain_candidate, list_candidates, show_candidate


def _store(
    root,
    candidate_id: str,
    *,
    candidate_type: str = "project_fact",
    risk_flags: list[str] | None = None,
    evidence: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
    candidate_text: str = "project fact candidate",
    source_message_ids: list[int] | None = None,
    source_turn_id: str = "turn-source",
    target_memory_layer: str = "candidate_memory",
    created_at: str = "2026-05-20T12:00:00+08:00",
) -> None:
    assert store_memory_candidate(
        root,
        candidate_id=candidate_id,
        candidate_type=candidate_type,
        source_message_ids=source_message_ids or [1, 2],
        source_turn_id=source_turn_id,
        candidate_text=candidate_text,
        confidence_score=80,
        target_gate="owner_memory_review",
        target_memory_layer=target_memory_layer,
        reason="extraction reason",
        risk_flags=risk_flags or ["memory_immune:review", "scope:owner_private"],
        evidence=evidence,
        provenance=provenance,
        review_notes="pending review",
        created_at=created_at,
    )


def test_memory_candidate_provenance_is_stored_and_explained(tmp_path) -> None:
    evidence = {
        "evidence_kind": "dialogue_turn",
        "source_scope": "owner_private",
        "source_turn_id": "turn-source",
        "source_message_count": 2,
        "confidence_score": 80,
        "immune_status": "allow_candidate",
        "immune_danger_level": "low",
        "immune_action": "allow_recent_context_candidate",
    }
    provenance = {
        "source_channel": "qq",
        "dialogue_scope": "owner_private",
        "privacy_scope": "owner_private",
        "event_time": "2026-05-20T12:00:00+08:00",
        "stable_memory_write_allowed": False,
        "promotion_requires_review": True,
    }
    _store(tmp_path, "memcand-provenance", evidence=evidence, provenance=provenance)

    row = list_memory_candidates(tmp_path, status="pending", limit=1)[0]
    explanation = explain_candidate(tmp_path, "memcand-provenance")

    assert row["source_turn_id"] == "turn-source"
    assert row["source_message_ids"] == [1, 2]
    assert row["risk_flags"] == ["memory_immune:review", "scope:owner_private"]
    assert row["evidence"] == evidence
    assert row["provenance"] == provenance
    assert explanation["ok"] is True
    assert explanation["source_turn_id"] == "turn-source"
    assert explanation["extraction_reason"] == "extraction reason"
    assert explanation["evidence"] == evidence
    assert explanation["provenance"] == provenance
    assert explanation["evidence_summary"]["source_scope"] == "owner_private"
    assert explanation["evidence_summary"]["immune_status"] == "allow_candidate"
    assert explanation["evidence_summary"]["stable_memory_write_allowed"] is False
    assert explanation["stable_memory_write"] == "blocked_until_review"


def test_memory_candidate_repeated_evidence_is_grouped_for_review(tmp_path) -> None:
    _store(
        tmp_path,
        "memcand-repeat-1",
        candidate_type="owner_preference",
        candidate_text="owner preference candidate\nowner_turn: please remember I prefer concise replies",
        source_message_ids=[11],
        source_turn_id="turn-repeat-1",
        target_memory_layer="memory/people/owner.md",
        created_at="2026-05-20T12:00:00+08:00",
    )
    _store(
        tmp_path,
        "memcand-repeat-2",
        candidate_type="owner_preference",
        candidate_text="owner preference candidate\nowner_turn: I prefer concise replies",
        source_message_ids=[12],
        source_turn_id="turn-repeat-2",
        target_memory_layer="memory/people/owner.md",
        created_at="2026-05-20T12:05:00+08:00",
    )

    explanation = explain_candidate(tmp_path, "memcand-repeat-2")

    review = explanation["memory_review"]
    assert review["evidence_count"] == 2
    assert review["supporting_candidate_ids"] == ["memcand-repeat-1"]
    assert review["conflicting_candidate_ids"] == []
    assert review["distinct_source_turn_count"] == 2
    assert review["recommendation"] == "repeated_evidence_ready_for_owner_review"


def test_memory_candidate_conflict_requires_explicit_resolution(tmp_path) -> None:
    _store(
        tmp_path,
        "memcand-conflict-positive",
        candidate_text="project fact candidate\nowner_turn: owner prefers concise replies",
        source_message_ids=[21],
        source_turn_id="turn-conflict-1",
        target_memory_layer="memory/context/recent_context.md",
        created_at="2026-05-20T12:00:00+08:00",
    )
    _store(
        tmp_path,
        "memcand-conflict-negative",
        candidate_text="project fact candidate\nowner_turn: owner does not prefer concise replies",
        source_message_ids=[22],
        source_turn_id="turn-conflict-2",
        target_memory_layer="memory/context/recent_context.md",
        created_at="2026-05-20T12:05:00+08:00",
    )

    explanation = explain_candidate(tmp_path, "memcand-conflict-negative")
    blocked = decide_candidate(tmp_path, "memcand-conflict-negative", decision="approve", review_notes="approve")
    approved = decide_candidate(
        tmp_path,
        "memcand-conflict-negative",
        decision="approve",
        review_notes="owner_resolved_conflict approve newer statement",
    )

    assert explanation["memory_review"]["conflicting_candidate_ids"] == ["memcand-conflict-positive"]
    assert explanation["memory_review"]["recommendation"] == "hold_conflict_review"
    assert blocked["ok"] is False
    assert blocked["error"] == "candidate_conflict_requires_owner_resolution"
    assert approved["ok"] is True
    assert approved["status"] == "approved"


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


def test_post_reply_growth_candidate_requires_explicit_owner_approval(tmp_path) -> None:
    _store(
        tmp_path,
        "memcand-growth-blocked",
        candidate_type="post_reply_growth_candidate",
        candidate_text="post-reply growth candidate; raw owner/reply text intentionally omitted",
        target_memory_layer="memory/reflection/growth_log.md",
    )

    blocked = decide_candidate(
        tmp_path,
        "memcand-growth-blocked",
        decision="approve",
        review_notes="looks good for growth log",
    )

    assert blocked["ok"] is False
    assert blocked["error"] == "high_risk_candidate_requires_explicit_owner_approval"


def test_approved_candidate_writes_promotion_preview_not_stable_memory(tmp_path) -> None:
    target = tmp_path / "memory/reflection/growth_log.md"
    _store(
        tmp_path,
        "memcand-growth-approved",
        candidate_type="post_reply_growth_candidate",
        candidate_text="post-reply growth candidate; raw owner/reply text intentionally omitted",
        target_memory_layer="memory/reflection/growth_log.md",
    )

    approved = decide_candidate(
        tmp_path,
        "memcand-growth-approved",
        decision="approve",
        review_notes="owner_approved_high_risk growth log preview ok",
    )

    assert approved["ok"] is True
    assert approved["status"] == "approved"
    assert approved["stable_memory_write"] == "dry_run_only"
    assert approved["apply_allowed"] is False
    assert approved["promotion_preview_blockers"]
    assert approved["promotion_preview_path"]
    assert not target.exists()
