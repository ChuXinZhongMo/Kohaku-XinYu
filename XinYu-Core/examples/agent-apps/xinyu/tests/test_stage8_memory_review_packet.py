from __future__ import annotations

from pathlib import Path

from xinyu_dialogue_archive import list_memory_candidates, store_memory_candidate, update_memory_candidate_status
from xinyu_stage8_memory_review_packet import (
    build_stage8_memory_review_packet,
    render_stage8_memory_review_packet,
    write_stage8_memory_review_packet,
    write_stage8_memory_review_packet_state,
)


def _store_owner_review_candidate(root: Path, candidate_id: str, *, raw_text: str) -> None:
    assert store_memory_candidate(
        root,
        candidate_id=candidate_id,
        candidate_type="owner_preference",
        source_message_ids=[101],
        source_turn_id=f"turn-{candidate_id}",
        candidate_text=f"owner preference candidate\nowner_turn: 模板感 private body must stay hidden {raw_text}",
        confidence_score=72,
        target_gate="owner_memory_review",
        target_memory_layer="memory/people/owner.md",
        reason="owner preference needs explicit review",
        risk_flags=["scope:owner_private", "danger:medium"],
        created_at="2026-05-29T18:00:00+08:00",
    )
    assert update_memory_candidate_status(
        root,
        candidate_id=candidate_id,
        status="owner_review_required",
        review_notes="needs owner decision",
    )


def test_stage8_memory_review_packet_hides_owner_body_and_is_read_only(tmp_path: Path) -> None:
    raw_private = "RAW_STAGE8_PACKET_OWNER_BODY_SHOULD_NOT_SURFACE_7101"
    _store_owner_review_candidate(tmp_path, "memcand-stage8-packet-owner", raw_text=raw_private)

    packet = build_stage8_memory_review_packet(tmp_path)
    rendered = render_stage8_memory_review_packet(packet)
    packet_path = write_stage8_memory_review_packet(tmp_path, packet)
    state_path = write_stage8_memory_review_packet_state(tmp_path, packet, packet_path=packet_path)
    state = state_path.read_text(encoding="utf-8")

    assert packet["packet_status"] == "ready_for_owner_review"
    assert packet["candidate_inventory"]["owner_review_required_count"] == 1
    item = packet["owner_review_required"][0]
    assert item["candidate_id"] == "memcand-stage8-packet-owner"
    assert item["candidate_type"] == "owner_preference"
    assert item["target_memory_layer"] == "memory/people/owner.md"
    assert item["candidate_text_preview"] == "hidden_owner_review_required"
    assert item["owner_private_body"] == "hidden"
    assert item["stable_memory_write"] == "blocked_until_explicit_owner_apply"
    assert item["review_topic_hint"] == "reply_style_template_or_mechanical"
    assert item["private_text_shape_detected"] is True
    assert "模板感 private body" not in item["approval_question"]
    assert "模板感 private body" not in rendered
    assert "负向偏好信号" in item["approval_question"]
    assert "模板感、机械感回复降权" in item["approval_question"]
    assert "不会直接写稳定记忆" in item["approval_impact"]["if_ok"]
    assert "owner_decision_required" in item["suggested_actions"]
    assert "high_risk_candidate_requires_explicit_owner_approval" in item["suggested_actions"]
    assert packet["boundaries"]["candidate_status_changed"] is False
    assert packet["boundaries"]["stable_memory_write"] == "blocked"
    assert raw_private not in str(packet)
    assert raw_private not in rendered
    assert raw_private not in packet_path.read_text(encoding="utf-8")
    assert raw_private not in state
    assert "candidate_body_in_packet: false" in state
    assert "qq_message_enqueued: false" in state
    assert not (tmp_path / "memory/people/owner.md").exists()
    assert [row["candidate_id"] for row in list_memory_candidates(tmp_path, status="owner_review_required", limit=5)] == [
        "memcand-stage8-packet-owner"
    ]
    assert not list_memory_candidates(tmp_path, status="approved", limit=5)
    assert not list_memory_candidates(tmp_path, status="rejected", limit=5)


def test_stage8_memory_review_packet_redacts_duplicate_cluster_bodies(tmp_path: Path) -> None:
    raw_duplicate = "RAW_STAGE8_PACKET_DUPLICATE_CLUSTER_SHOULD_NOT_SURFACE_7102"
    for index in range(2):
        assert store_memory_candidate(
            tmp_path,
            candidate_id=f"memcand-stage8-dup-{index}",
            candidate_type="project_fact",
            source_message_ids=[201 + index],
            source_turn_id=f"turn-stage8-dup-{index}",
            candidate_text=f"project fact candidate: {raw_duplicate}",
            confidence_score=70,
            target_gate="recent_context_project_review",
            target_memory_layer="memory/context/recent_context.md",
            reason="project continuity",
            risk_flags=["scope:system_maintenance"],
            created_at="2026-05-29T18:00:00+08:00",
        )

    packet = build_stage8_memory_review_packet(tmp_path, max_clusters=5)
    rendered = render_stage8_memory_review_packet(packet)

    assert packet["candidate_inventory"]["duplicate_cluster_count"] >= 1
    cluster = next(item for item in packet["duplicate_cluster_backlog"] if item["size"] == 2)
    assert set(cluster["sample_candidate_ids"]) == {"memcand-stage8-dup-0", "memcand-stage8-dup-1"}
    assert cluster["candidate_text_preview"] == "hidden_for_cluster_backlog"
    assert "do_not_treat_duplicate_cluster_as_fact" in cluster["suggested_actions"]
    assert raw_duplicate not in str(packet)
    assert raw_duplicate not in rendered
