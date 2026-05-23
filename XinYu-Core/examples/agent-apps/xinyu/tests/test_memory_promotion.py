from __future__ import annotations

from pathlib import Path

from xinyu_dialogue_archive import list_memory_candidates, store_memory_candidate, update_memory_candidate_status
from xinyu_memory_promotion import apply_stable_memory_promotion, build_stable_memory_promotion_dry_run


def test_stable_memory_promotion_dry_run_renders_diff_without_writing(tmp_path: Path) -> None:
    target = tmp_path / "memory/context/recent_context.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Recent Context\n\nexisting\n", encoding="utf-8")
    assert store_memory_candidate(
        tmp_path,
        candidate_id="memcand-dry-run",
        candidate_type="project_fact",
        source_message_ids=[1, 2],
        source_turn_id="turn-1",
        candidate_text="project fact candidate\nowner_turn: dry-run promotion should preview only",
        confidence_score=80,
        target_gate="recent_context_project_review",
        target_memory_layer="memory/context/recent_context.md",
        reason="project continuity",
        risk_flags=["scope:owner_private"],
        evidence={"claim_key": "claim-1", "claim_topic_key": "topic-1"},
        provenance={"stable_memory_write_allowed": False, "promotion_requires_review": True},
        created_at="2026-05-20T12:00:00+08:00",
    )
    assert update_memory_candidate_status(
        tmp_path,
        candidate_id="memcand-dry-run",
        status="approved",
        review_notes="owner reviewed candidate",
    )

    before = target.read_text(encoding="utf-8")
    result = build_stable_memory_promotion_dry_run(
        tmp_path,
        "memcand-dry-run",
        write_preview=True,
        generated_at="2026-05-22T00:00:00+08:00",
    )

    assert result["ok"] is True
    assert result["apply_allowed"] is False
    assert "candidate_type_not_supported_for_stable_apply" in result["blockers"]
    assert result["stable_memory_write"] == "dry_run_only"
    assert "Candidate Promotion Draft: memcand-dry-run" in result["proposed_entry"]
    assert "+## Candidate Promotion Draft: memcand-dry-run" in result["diff"]
    assert target.read_text(encoding="utf-8") == before
    preview = Path(result["preview_path"])
    assert preview.exists()
    assert "stable_memory_write: dry_run_only" in preview.read_text(encoding="utf-8")


def _store_approved_growth_candidate(root: Path, candidate_id: str = "memcand-growth-apply") -> None:
    assert store_memory_candidate(
        root,
        candidate_id=candidate_id,
        candidate_type="post_reply_growth_candidate",
        source_message_ids=[11],
        source_turn_id="turn-growth-apply",
        candidate_text="post-reply growth candidate; raw owner/reply text intentionally omitted",
        confidence_score=76,
        target_gate="personality_growth_review",
        target_memory_layer="memory/reflection/growth_log.md",
        reason="repeated post-reply success plus owner positive feedback",
        risk_flags=["memory_immune:review", "scope:owner_private"],
        created_at="2026-05-20T12:00:00+08:00",
    )
    assert update_memory_candidate_status(
        root,
        candidate_id=candidate_id,
        status="approved",
        review_notes="owner_approved_high_risk growth log preview ok",
    )


def test_apply_growth_candidate_requires_owner_apply_confirmation(tmp_path: Path) -> None:
    _store_approved_growth_candidate(tmp_path)

    result = apply_stable_memory_promotion(tmp_path, "memcand-growth-apply", review_notes="looks good")

    assert result["ok"] is False
    assert result["error"] == "owner_apply_confirmation_required"
    assert not (tmp_path / "memory/reflection/growth_log.md").exists()


def test_apply_growth_candidate_appends_growth_log_and_marks_status(tmp_path: Path) -> None:
    target = tmp_path / "memory/reflection/growth_log.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Growth Log\n\nexisting\n", encoding="utf-8")
    _store_approved_growth_candidate(tmp_path)
    preview = build_stable_memory_promotion_dry_run(
        tmp_path,
        "memcand-growth-apply",
        generated_at="2026-05-22T00:00:00+08:00",
    )

    result = apply_stable_memory_promotion(
        tmp_path,
        "memcand-growth-apply",
        review_notes="owner_apply_confirmed after preview",
        expected_before_hash=preview["before_hash"],
        applied_at="2026-05-22T00:01:00+08:00",
    )

    text = target.read_text(encoding="utf-8")
    assert result["ok"] is True
    assert result["status"] == "applied_growth_log"
    assert result["stable_memory_write"] == "applied_growth_log_only"
    assert result["stable_personality_write"] == "blocked"
    assert "existing" in text
    assert "Candidate Promotion Draft: memcand-growth-apply" in text
    assert list_memory_candidates(tmp_path, status="applied_growth_log", limit=5)[0]["candidate_id"] == "memcand-growth-apply"


def test_apply_growth_candidate_rejects_stale_preview_hash(tmp_path: Path) -> None:
    target = tmp_path / "memory/reflection/growth_log.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Growth Log\n", encoding="utf-8")
    _store_approved_growth_candidate(tmp_path)
    preview = build_stable_memory_promotion_dry_run(tmp_path, "memcand-growth-apply")
    target.write_text("# Growth Log\n\nchanged\n", encoding="utf-8")

    result = apply_stable_memory_promotion(
        tmp_path,
        "memcand-growth-apply",
        review_notes="owner_apply_confirmed after preview",
        expected_before_hash=preview["before_hash"],
    )

    assert result["ok"] is False
    assert result["error"] == "target_changed_since_preview"
    assert "Candidate Promotion Draft" not in target.read_text(encoding="utf-8")
