from __future__ import annotations

from pathlib import Path

from xinyu_dialogue_archive import list_memory_candidates, store_memory_candidate, update_memory_candidate_status
from xinyu_memory_candidate_maintenance import run_memory_candidate_maintenance


def _store(root: Path, candidate_id: str, *, created_at: str) -> None:
    assert store_memory_candidate(
        root,
        candidate_id=candidate_id,
        candidate_type="owner_preference",
        source_message_ids=[1],
        source_turn_id="turn-old",
        candidate_text="owner preference candidate\nowner_turn: I prefer concise replies",
        confidence_score=60,
        target_gate="owner_memory_review",
        target_memory_layer="memory/people/owner.md",
        reason="possible owner preference",
        risk_flags=["scope:owner_private"],
        created_at=created_at,
    )


def test_memory_candidate_maintenance_backfills_claim_metadata_and_archives_stale_observe_more(tmp_path: Path) -> None:
    _store(tmp_path, "old-observe", created_at="2026-04-01T00:00:00+08:00")
    assert update_memory_candidate_status(
        tmp_path,
        candidate_id="old-observe",
        status="observe_more_owner_preference",
        review_notes="observe for repetition",
    )

    result = run_memory_candidate_maintenance(
        tmp_path,
        checked_at="2026-05-22T00:00:00+08:00",
        write_state=True,
    )

    archived = list_memory_candidates(tmp_path, status="archived_observe_more", limit=5)
    assert result["backfill"]["backfilled"] == 1
    assert result["cleanup"]["archived"] == 1
    assert archived[0]["candidate_id"] == "old-observe"
    assert archived[0]["evidence"]["claim_key"]
    assert archived[0]["provenance"]["promotion_requires_review"] is True
    state = (tmp_path / "memory/context/memory_candidate_maintenance_state.md").read_text(encoding="utf-8")
    assert "backfilled: 1" in state
    assert "archived: 1" in state
