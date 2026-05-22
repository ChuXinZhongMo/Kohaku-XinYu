from __future__ import annotations

from pathlib import Path

from xinyu_dialogue_archive import store_memory_candidate, update_memory_candidate_status
from xinyu_memory_promotion import build_stable_memory_promotion_dry_run


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
    assert result["stable_memory_write"] == "dry_run_only"
    assert "Candidate Promotion Draft: memcand-dry-run" in result["proposed_entry"]
    assert "+## Candidate Promotion Draft: memcand-dry-run" in result["diff"]
    assert target.read_text(encoding="utf-8") == before
    preview = Path(result["preview_path"])
    assert preview.exists()
    assert "stable_memory_write: dry_run_only" in preview.read_text(encoding="utf-8")
