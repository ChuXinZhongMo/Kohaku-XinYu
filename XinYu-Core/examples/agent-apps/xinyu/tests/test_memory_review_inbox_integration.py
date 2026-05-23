from __future__ import annotations

import json
from pathlib import Path

from xinyu_dialogue_archive import list_memory_candidates, store_memory_candidate, update_memory_candidate_status
from xinyu_review_inbox import handle_review_inbox_command, run_review_inbox_maintenance
from xinyu_visible_persona_voice import compose_review_inbox_card


def _store_owner_review_candidate(
    root: Path,
    candidate_id: str,
    *,
    candidate_type: str = "owner_preference",
    target_gate: str = "owner_memory_review",
    target_memory_layer: str = "memory/people/owner.md",
    candidate_text: str | None = None,
) -> None:
    assert store_memory_candidate(
        root,
        candidate_id=candidate_id,
        candidate_type=candidate_type,
        source_message_ids=[1],
        source_turn_id=f"turn-{candidate_id}",
        candidate_text=candidate_text or f"owner preference candidate\nowner_turn: {candidate_id} should be reviewed",
        confidence_score=75,
        target_gate=target_gate,
        target_memory_layer=target_memory_layer,
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
    assert "不会直接写稳定记忆" in compose_review_inbox_card(cursor)

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


def test_review_inbox_growth_candidate_shows_apply_boundary(tmp_path: Path) -> None:
    _store_owner_review_candidate(
        tmp_path,
        "memcand-growth-inbox",
        candidate_type="post_reply_growth_candidate",
        target_gate="post_reply_growth_review",
        target_memory_layer="memory/reflection/growth_log.md",
        candidate_text=(
            "growth observation\n"
            "signals: owner_positive_feedback,repeated_success\n"
            "pattern: XinYu should keep using the short repair style."
        ),
    )

    run_review_inbox_maintenance(tmp_path, owner_user_id="42", max_items=1)
    cursor = _read_json(tmp_path / "memory/context/review_inbox_cursor.json")

    summary = cursor["items"][0]["summary"]
    card = compose_review_inbox_card(cursor)
    assert "writes preview only" in summary
    assert "local apply is required for growth_log" in summary
    assert "!ok 只表示同意候选并生成本地预览" in card
    assert "成长日志还要本地 apply" in card


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
