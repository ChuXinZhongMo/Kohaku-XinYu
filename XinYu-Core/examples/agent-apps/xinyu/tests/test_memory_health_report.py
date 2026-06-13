from __future__ import annotations

from xinyu_dialogue_archive import store_memory_candidate, update_memory_candidate_status
from xinyu_memory_health_report import build_memory_health_report, render_memory_health_report


def test_memory_health_report_hides_owner_private_candidate_text(tmp_path) -> None:
    raw_private = "RAW_MEMORY_HEALTH_OWNER_PRIVATE_TEXT_SHOULD_NOT_SURFACE_5831"
    assert store_memory_candidate(
        tmp_path,
        candidate_id="memcand-health-owner",
        candidate_type="owner_preference",
        source_message_ids=[1],
        source_turn_id="turn-health-owner",
        candidate_text=f"owner_turn: {raw_private}",
        confidence_score=82,
        target_gate="owner_memory_review",
        target_memory_layer="memory/people/owner.md",
        reason="owner preference requires explicit review",
        risk_flags=["memory_immune:review", "scope:owner_private"],
        evidence={"claim_topic_key": "owner.preference", "claim_polarity": "positive"},
        review_notes="pending owner review",
    )
    assert update_memory_candidate_status(
        tmp_path,
        candidate_id="memcand-health-owner",
        status="owner_review_required",
        review_notes="needs owner review",
    )

    report = build_memory_health_report(tmp_path)
    rendered = render_memory_health_report(report)

    assert report["candidate_inventory"]["owner_review_required_count"] == 1
    assert report["candidate_inventory"]["private_or_owner_scoped_count"] == 1
    assert report["owner_review_required"][0]["candidate_id"] == "memcand-health-owner"
    assert report["owner_review_required"][0]["candidate_text_preview"] == "hidden_private_or_owner_review_required"
    assert report["privacy_boundary"]["owner_memory_write"] == "blocked_without_explicit_owner_apply"
    assert "keep_owner_private_candidate_body_hidden" in report["recommendations"]
    assert "- stable_memory_write: blocked" in rendered
    assert "candidate_text_preview=hidden_owner_review_required" in rendered
    assert raw_private not in str(report)
    assert raw_private not in rendered
