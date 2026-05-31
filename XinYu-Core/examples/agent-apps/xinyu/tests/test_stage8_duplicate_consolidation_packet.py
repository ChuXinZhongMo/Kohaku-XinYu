from __future__ import annotations

from pathlib import Path

from xinyu_dialogue_archive import list_memory_candidates, store_memory_candidate
from xinyu_memory_health_report import build_memory_health_report, render_memory_health_report
from xinyu_stage8_duplicate_consolidation_packet import (
    ARCHIVED_DUPLICATE_STATUS,
    apply_stage8_duplicate_consolidation,
    build_stage8_duplicate_consolidation_packet,
    render_stage8_duplicate_consolidation_packet,
    write_stage8_duplicate_consolidation_packet,
    write_stage8_duplicate_consolidation_state,
)


def _store_candidate(root: Path, candidate_id: str, *, text: str, created_at: str) -> None:
    assert store_memory_candidate(
        root,
        candidate_id=candidate_id,
        candidate_type="project_fact",
        source_message_ids=[101],
        source_turn_id=f"turn-{candidate_id}",
        candidate_text=text,
        confidence_score=70,
        target_gate="recent_context_project_review",
        target_memory_layer="memory/context/recent_context.md",
        reason="project continuity",
        risk_flags=["scope:system_maintenance"],
        created_at=created_at,
    )


def test_stage8_duplicate_consolidation_packet_is_redacted_and_read_only(tmp_path: Path) -> None:
    raw_duplicate = "RAW_STAGE8_DUPLICATE_CONSOLIDATION_BODY_SHOULD_NOT_SURFACE_9101"
    for index in range(2):
        _store_candidate(
            tmp_path,
            f"memcand-stage8-dedupe-{index}",
            text=f"project fact candidate: duplicate followup marker {raw_duplicate}",
            created_at=f"2026-05-29T18:0{index}:00+08:00",
        )

    packet = build_stage8_duplicate_consolidation_packet(tmp_path, max_clusters=5)
    rendered = render_stage8_duplicate_consolidation_packet(packet)
    packet_path = write_stage8_duplicate_consolidation_packet(tmp_path, packet)
    state_path = write_stage8_duplicate_consolidation_state(tmp_path, packet, packet_path=packet_path)
    state = state_path.read_text(encoding="utf-8")

    assert packet["packet_status"] == "ready_for_consolidation_review"
    assert packet["summary"]["duplicate_cluster_count"] == 1
    assert packet["summary"]["consolidation_item_count"] == 1
    proposal = packet["consolidation_proposals"][0]
    assert proposal["size"] == 2
    assert set(proposal["sample_candidate_ids"]) == {
        "memcand-stage8-dedupe-0",
        "memcand-stage8-dedupe-1",
    }
    assert proposal["candidate_text_preview"] == "hidden_duplicate_consolidation"
    assert proposal["stable_memory_write"] == "blocked"
    assert proposal["candidate_status_change"] == "none"
    assert proposal["merge_readiness"] == "review_ready"
    assert packet["boundaries"]["candidate_status_changed"] is False
    assert packet["boundaries"]["stable_memory_write"] == "blocked"
    assert "candidate_status_changed: false" in rendered
    assert "stable_memory_write: blocked" in rendered
    assert raw_duplicate not in str(packet)
    assert raw_duplicate not in rendered
    assert raw_duplicate not in packet_path.read_text(encoding="utf-8")
    assert raw_duplicate not in state
    assert "candidate_body_in_packet: false" in state
    assert not (tmp_path / "memory/context/recent_context.md").exists()
    assert {
        row["candidate_id"] for row in list_memory_candidates(tmp_path, status="pending", limit=5)
    } == {"memcand-stage8-dedupe-0", "memcand-stage8-dedupe-1"}
    assert not list_memory_candidates(tmp_path, status="approved", limit=5)
    assert not list_memory_candidates(tmp_path, status="rejected", limit=5)
    assert not list_memory_candidates(tmp_path, status="applied_growth_log", limit=5)


def test_memory_health_report_tracks_duplicate_consolidation_state(tmp_path: Path) -> None:
    for index in range(2):
        _store_candidate(
            tmp_path,
            f"memcand-stage8-health-dedupe-{index}",
            text="project fact candidate: health duplicate topic",
            created_at=f"2026-05-29T18:1{index}:00+08:00",
        )

    missing_report = build_memory_health_report(tmp_path)
    missing_stage8 = missing_report["stage8_memory_governance"]
    assert missing_report["duplicate_consolidation"]["duplicate_consolidation_status"] == "missing"
    assert missing_stage8["duplicate_consolidation_status"] == "missing"
    assert "write_or_refresh_stage8_duplicate_consolidation_packet" in missing_report["recommendations"]

    packet = build_stage8_duplicate_consolidation_packet(tmp_path, max_clusters=5)
    packet_path = write_stage8_duplicate_consolidation_packet(tmp_path, packet)
    write_stage8_duplicate_consolidation_state(tmp_path, packet, packet_path=packet_path)

    ready_report = build_memory_health_report(tmp_path)
    ready_rendered = render_memory_health_report(ready_report)
    ready_stage8 = ready_report["stage8_memory_governance"]
    assert ready_report["duplicate_consolidation"]["duplicate_consolidation_status"] == "ready"
    assert ready_stage8["duplicate_consolidation_status"] == "ready"
    assert ready_stage8["duplicate_consolidation_item_count"] == 1
    assert ready_stage8["duplicate_consolidation_ready_cluster_count"] == 1
    assert str(packet_path.as_posix()) in ready_stage8["duplicate_consolidation_packet_path"]
    assert "duplicate_consolidation_status: ready" in ready_rendered

    for index in range(2):
        _store_candidate(
            tmp_path,
            f"memcand-stage8-health-second-dedupe-{index}",
            text="project fact candidate: second health duplicate topic",
            created_at=f"2026-05-29T18:2{index}:00+08:00",
        )

    stale_report = build_memory_health_report(tmp_path)
    assert stale_report["duplicate_cluster_count"] == 2
    assert stale_report["duplicate_consolidation"]["duplicate_consolidation_status"] == "stale"
    assert stale_report["stage8_memory_governance"]["duplicate_consolidation_status"] == "stale"
    assert "write_or_refresh_stage8_duplicate_consolidation_packet" in stale_report["recommendations"]


def test_stage8_duplicate_consolidation_apply_archives_only_non_representatives(tmp_path: Path) -> None:
    for index in range(3):
        _store_candidate(
            tmp_path,
            f"memcand-stage8-apply-dedupe-{index}",
            text="project fact candidate: apply duplicate topic",
            created_at=f"2026-05-29T18:3{index}:00+08:00",
        )

    blocked = apply_stage8_duplicate_consolidation(tmp_path)
    assert blocked["ok"] is False
    assert blocked["error"] == "owner_approved_consolidation_required"
    assert blocked["candidate_status_changed"] is False
    assert build_memory_health_report(tmp_path)["duplicate_cluster_count"] == 1

    result = apply_stage8_duplicate_consolidation(
        tmp_path,
        owner_approved_consolidation=True,
        applied_at="2026-05-29T18:40:00+08:00",
    )

    assert result["ok"] is True
    assert result["stable_memory_write"] == "blocked"
    assert result["candidate_status_changed"] is True
    assert result["candidate_body_changed"] is False
    assert result["archived_candidate_count"] == 2
    pending = list_memory_candidates(tmp_path, status="pending", limit=5)
    archived = list_memory_candidates(tmp_path, status=ARCHIVED_DUPLICATE_STATUS, limit=5)
    assert len(pending) == 1
    assert {row["candidate_id"] for row in archived} == {
        "memcand-stage8-apply-dedupe-0",
        "memcand-stage8-apply-dedupe-1",
    }
    assert all("stage8_duplicate_consolidation" in row["review_notes"] for row in archived)
    report = build_memory_health_report(tmp_path)
    assert report["duplicate_cluster_count"] == 0
    assert report["stage8_memory_governance"]["duplicate_cluster_count"] == 0
    assert report["duplicate_consolidation"]["duplicate_consolidation_status"] == "not_required"
    assert not (tmp_path / "memory/context/recent_context.md").exists()
