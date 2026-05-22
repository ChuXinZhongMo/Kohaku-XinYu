from __future__ import annotations

import json
from pathlib import Path

from xinyu_dialogue_archive import list_memory_candidates, store_memory_candidate, update_memory_candidate_status
from xinyu_review_inbox import handle_review_inbox_command, run_review_inbox_maintenance


def _store_owner_review_candidate(root: Path, candidate_id: str) -> None:
    assert store_memory_candidate(
        root,
        candidate_id=candidate_id,
        candidate_type="owner_preference",
        source_message_ids=[1],
        source_turn_id=f"turn-{candidate_id}",
        candidate_text=f"owner preference candidate\nowner_turn: {candidate_id} should be reviewed",
        confidence_score=75,
        target_gate="owner_memory_review",
        target_memory_layer="memory/people/owner.md",
        reason=f"{candidate_id} needs owner review",
        risk_flags=["memory_immune:review", "scope:owner_private"],
        created_at="2026-05-20T12:00:00+08:00",
    )
    assert update_memory_candidate_status(
        root,
        candidate_id=candidate_id,
        status="owner_review_required",
        review_notes="owner review required",
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_review_inbox_ok_approves_memory_candidate_without_stable_promotion(tmp_path: Path) -> None:
    _store_owner_review_candidate(tmp_path, "memcand-inbox-ok")

    first = run_review_inbox_maintenance(tmp_path, owner_user_id="42", max_items=1)
    cursor = _read_json(tmp_path / "memory/context/review_inbox_cursor.json")

    assert first["pending_count"] == 1
    assert cursor["items"][0]["source_kind"] == "memory_candidate"
    assert "not stable memory" in cursor["items"][0]["summary"]

    handled = handle_review_inbox_command(
        tmp_path,
        {
            "command": "ok",
            "indices": ["1"],
            "user_id": "42",
            "message_id": "m-memory-ok",
        },
    )

    assert handled["accepted"] is True
    assert handled["processed_count"] == 1
    assert handled["apply_results"][0]["status"] == "approved"
    approved = list_memory_candidates(tmp_path, status="approved", limit=5)
    assert [row["candidate_id"] for row in approved] == ["memcand-inbox-ok"]
    assert not (tmp_path / "memory/people/owner.md").exists()


def test_review_inbox_rej_rejects_memory_candidate(tmp_path: Path) -> None:
    _store_owner_review_candidate(tmp_path, "memcand-inbox-rej")

    run_review_inbox_maintenance(tmp_path, owner_user_id="42", max_items=1)
    handled = handle_review_inbox_command(
        tmp_path,
        {
            "command": "rej",
            "indices": ["1"],
            "user_id": "42",
            "message_id": "m-memory-rej",
        },
    )

    assert handled["accepted"] is True
    assert handled["processed_count"] == 1
    assert handled["apply_results"][0]["status"] == "rejected"
    rejected = list_memory_candidates(tmp_path, status="rejected", limit=5)
    assert [row["candidate_id"] for row in rejected] == ["memcand-inbox-rej"]
