from __future__ import annotations

import json
from pathlib import Path

from xinyu_dialogue_archive import list_memory_candidates, store_memory_candidate, update_memory_candidate_status
from xinyu_memory_health_report import (
    build_memory_health_report,
    render_memory_health_report,
    write_stage8_memory_governance_state,
)
from xinyu_memory_promotion import (
    apply_stable_memory_promotion,
    build_stable_memory_promotion_dry_run,
    list_growth_candidate_promotions,
)


def _write_stage7_ready_trace(root: Path) -> None:
    rows = []
    for index in range(3):
        rows.append(
            {
                "checked_at": f"2026-05-29T18:0{index}:00+08:00",
                "ecology_id": f"eco-stage8-ready-{index}",
                "feedback_consumption_status": "consumed",
                "feedback_consumed_sources": "action_feedback:qq_visible_reply_ack",
                "feedback_consumed_biases": "action_feedback_bias:route_confirmed_visible_reply_risk:-4",
                "feedback_consumed_future_effect": "action_feedback_future:confirm_visible_reply_transport",
            }
        )
    trace_path = root / "runtime/intention_ecology_trace.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


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


def test_list_growth_candidate_promotions_pending_is_read_only(tmp_path: Path) -> None:
    target = tmp_path / "memory/reflection/growth_log.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Growth Log\n", encoding="utf-8")
    _store_approved_growth_candidate(tmp_path)
    before = target.read_text(encoding="utf-8")

    result = list_growth_candidate_promotions(tmp_path)

    assert result["ok"] is True
    assert result["pending_apply_count"] == 1
    item = result["pending_apply"][0]
    assert item["candidate_id"] == "memcand-growth-apply"
    assert item["apply_allowed"] is False
    assert item["stable_memory_write"] == "dry_run_only"
    assert item["stable_personality_write"] == "blocked"
    assert item["before_hash"]
    assert item["apply_command"] == (
        "python xinyu_memory_candidate_review_cli.py apply memcand-growth-apply "
        f"--notes \"owner_apply_confirmed after preview\" --expected-before-hash {item['before_hash']}"
    )
    assert target.read_text(encoding="utf-8") == before
    assert list_memory_candidates(tmp_path, status="approved", limit=5)[0]["candidate_id"] == "memcand-growth-apply"
    assert not (tmp_path / "runtime/memory_promotion_dry_runs/memcand-growth-apply.md").exists()


def test_list_growth_candidate_promotions_surfaces_owner_review_without_body(tmp_path: Path) -> None:
    assert store_memory_candidate(
        tmp_path,
        candidate_id="memcand-owner-review",
        candidate_type="owner_preference",
        source_message_ids=[21],
        source_turn_id="turn-owner-review",
        candidate_text="private owner preference body must not be exposed on desktop",
        confidence_score=72,
        target_gate="owner_memory_review",
        target_memory_layer="memory/people/owner.md",
        reason="owner preference needs explicit review",
        risk_flags=["scope:owner_private", "danger:medium"],
        created_at="2026-05-20T12:00:00+08:00",
    )
    assert update_memory_candidate_status(
        tmp_path,
        candidate_id="memcand-owner-review",
        status="owner_review_required",
        review_notes="needs owner decision",
    )

    result = list_growth_candidate_promotions(tmp_path)

    assert result["owner_review_required_count"] == 1
    item = result["owner_review_required"][0]
    assert item["candidate_id"] == "memcand-owner-review"
    assert item["target_memory_layer"] == "memory/people/owner.md"
    assert item["stable_memory_write"] == "owner_review_required"
    assert item["candidate_text_preview"] == "hidden_owner_review_required"
    assert "private owner preference" not in str(item)
    assert "owner_review_body_hidden" in result["notes"]


def test_list_growth_candidate_promotions_counts_applied(tmp_path: Path) -> None:
    target = tmp_path / "memory/reflection/growth_log.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Growth Log\n", encoding="utf-8")
    _store_approved_growth_candidate(tmp_path)
    preview = build_stable_memory_promotion_dry_run(tmp_path, "memcand-growth-apply")
    apply_result = apply_stable_memory_promotion(
        tmp_path,
        "memcand-growth-apply",
        review_notes="owner_apply_confirmed after preview",
        expected_before_hash=preview["before_hash"],
    )
    assert apply_result["ok"] is True

    result = list_growth_candidate_promotions(tmp_path)

    assert result["pending_apply_count"] == 0
    assert result["applied_count"] == 1
    assert result["applied"][0]["candidate_id"] == "memcand-growth-apply"


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


def test_memory_health_report_hides_owner_review_body_and_keeps_writes_blocked(tmp_path: Path) -> None:
    assert store_memory_candidate(
        tmp_path,
        candidate_id="memcand-owner-health",
        candidate_type="owner_preference",
        source_message_ids=[31],
        source_turn_id="turn-owner-health",
        candidate_text="private owner preference body must not leak from health report",
        confidence_score=71,
        target_gate="owner_memory_review",
        target_memory_layer="memory/people/owner.md",
        reason="owner preference needs explicit review",
        risk_flags=["scope:owner_private", "danger:medium"],
        created_at="2026-05-20T12:00:00+08:00",
    )
    assert update_memory_candidate_status(
        tmp_path,
        candidate_id="memcand-owner-health",
        status="owner_review_required",
        review_notes="needs owner decision",
    )

    report = build_memory_health_report(tmp_path)
    rendered = render_memory_health_report(report)

    assert report["candidate_inventory"]["owner_review_required_count"] == 1
    assert report["privacy_boundary"]["owner_review_candidate_text"] == "hidden"
    assert report["privacy_boundary"]["owner_memory_write"] == "blocked_without_explicit_owner_apply"
    assert report["privacy_boundary"]["stable_personality_write"] == "blocked_review_only"
    assert report["owner_review_required"][0]["candidate_text_preview"] == "hidden_private_or_owner_review_required"
    assert "private owner preference body" not in str(report)
    assert "private owner preference body" not in rendered
    assert "candidate_text_preview=hidden_owner_review_required" in rendered


def test_memory_health_report_clusters_related_candidates_without_private_text(tmp_path: Path) -> None:
    for candidate_id, text in (
        ("memcand-health-1", "project fact candidate: Codex followup should remain active after timeout"),
        ("memcand-health-2", "project fact candidate: Codex followup should remain active after timeout"),
    ):
        assert store_memory_candidate(
            tmp_path,
            candidate_id=candidate_id,
            candidate_type="project_fact",
            source_message_ids=[41],
            source_turn_id=f"turn-{candidate_id}",
            candidate_text=text,
            confidence_score=70,
            target_gate="recent_context_project_review",
            target_memory_layer="memory/context/recent_context.md",
            reason="project continuity",
            risk_flags=["scope:system_maintenance"],
            created_at="2026-05-20T12:00:00+08:00",
        )

    report = build_memory_health_report(tmp_path)

    assert report["duplicate_cluster_count"] >= 1
    cluster = next(item for item in report["clusters"] if item["size"] == 2)
    assert cluster["status_counts"] == {"pending": 2}
    assert {item["candidate_id"] for item in cluster["items"]} == {"memcand-health-1", "memcand-health-2"}


def test_memory_health_report_hides_dialogue_and_voice_previews_without_private_flags(tmp_path: Path) -> None:
    raw_dialogue = "RAW_DIALOGUE_PREVIEW_SHOULD_NOT_SURFACE_9142"
    raw_voice = "RAW_VOICE_PREVIEW_SHOULD_NOT_SURFACE_9142"
    assert store_memory_candidate(
        tmp_path,
        candidate_id="memcand-dialogue-preview",
        candidate_type="project_fact",
        source_message_ids=[51],
        source_turn_id="turn-dialogue-preview",
        candidate_text=f"project fact candidate; owner_turn: {raw_dialogue} visible_reply: still private",
        confidence_score=70,
        target_gate="recent_context_project_review",
        target_memory_layer="memory/context/recent_context.md",
        reason="project continuity",
        risk_flags=["scope:system_maintenance"],
        created_at="2026-05-20T12:00:00+08:00",
    )
    assert store_memory_candidate(
        tmp_path,
        candidate_id="memcand-voice-preview",
        candidate_type="voice_correction",
        source_message_ids=[52],
        source_turn_id="turn-voice-preview",
        candidate_text=f"voice correction candidate; {raw_voice}",
        confidence_score=70,
        target_gate="voice_calibration_review",
        target_memory_layer="memory/self/voice_calibration_log.md",
        reason="voice calibration",
        risk_flags=[],
        created_at="2026-05-20T12:00:00+08:00",
    )

    report = build_memory_health_report(tmp_path)
    rendered = render_memory_health_report(report)
    cluster_items = [item for cluster in report["clusters"] for item in cluster["items"]]
    dialogue_item = next(item for item in cluster_items if item["candidate_id"] == "memcand-dialogue-preview")
    voice_item = next(item for item in cluster_items if item["candidate_id"] == "memcand-voice-preview")

    assert dialogue_item["candidate_text_preview"] == "hidden_private_or_owner_review_required"
    assert voice_item["candidate_text_preview"] == "hidden_private_or_owner_review_required"
    assert report["candidate_inventory"]["private_or_owner_scoped_count"] == 2
    assert raw_dialogue not in str(report)
    assert raw_dialogue not in rendered
    assert raw_voice not in str(report)
    assert raw_voice not in rendered


def test_memory_health_report_surfaces_stage8_governance_without_private_text(tmp_path: Path) -> None:
    raw_private = "RAW_STAGE8_MEMORY_GOVERNANCE_SHOULD_NOT_SURFACE_8142"
    _write_stage7_ready_trace(tmp_path)
    assert store_memory_candidate(
        tmp_path,
        candidate_id="memcand-stage8-owner-review",
        candidate_type="owner_preference",
        source_message_ids=[61],
        source_turn_id="turn-stage8-owner-review",
        candidate_text=f"private owner preference body must stay hidden {raw_private}",
        confidence_score=72,
        target_gate="owner_memory_review",
        target_memory_layer="memory/people/owner.md",
        reason="owner preference needs explicit review",
        risk_flags=["scope:owner_private", "danger:medium"],
        created_at="2026-05-29T18:00:00+08:00",
    )
    assert update_memory_candidate_status(
        tmp_path,
        candidate_id="memcand-stage8-owner-review",
        status="owner_review_required",
        review_notes="needs owner decision",
    )

    report = build_memory_health_report(tmp_path)
    rendered = render_memory_health_report(report)
    state_path = write_stage8_memory_governance_state(tmp_path, report)
    state = state_path.read_text(encoding="utf-8")
    stage8 = report["stage8_memory_governance"]

    assert stage8["status"] == "active_guarded"
    assert stage8["ready_for_stage9"] is False
    assert stage8["stage7_ready_for_stage8"] is True
    assert stage8["owner_review_required_count"] == 1
    assert stage8["owner_review_candidate_text"] == "hidden"
    assert stage8["stable_identity_profile_apply"] == "blocked"
    assert stage8["next_step"] == "review_owner_required_memory_candidates_in_owner_channel_only"
    assert "stage8_memory_governance_status: active_guarded" in state
    assert raw_private not in str(report)
    assert raw_private not in rendered
    assert raw_private not in state


def test_memory_health_report_surfaces_learning_trial_gate(tmp_path: Path) -> None:
    state = tmp_path / "memory/self/learning_closed_loop_state.md"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(
        """# Learning Closed Loop State

## Current Loop
- status: trial_active
- active_trial_habit: replace_explanations_with_one_concrete_owner-facing_line_under_style_pressure
- active_trial_key: owner_reported_template_voice_failure
- repair_count: 12
- success_count: 0
- success_streak: 0
- trial_success_count: 0
- trial_success_streak: 0
- promotion_signal: false
- latest_success_trial_key: none
- success_evidence_status: reset_by_failure
- last_owner_reaction: repair_pressure_overloaded
""",
        encoding="utf-8",
    )

    report = build_memory_health_report(tmp_path)
    rendered = render_memory_health_report(report)

    assert report["personality"]["learning_trial_success_gate"] == "blocked"
    assert report["personality"]["learning_trial_active_key"] == "owner_reported_template_voice_failure"
    assert report["personality"]["learning_trial_success_evidence_status"] == "reset_by_failure"
    assert report["personality"]["learning_trial_repair_count"] == 12
    assert report["personality"]["learning_trial_success_count"] == 0
    assert "keep_trial_habit_out_of_stable_profile_until_learning_success_repeats" in report["recommendations"]
    assert "learning_trial_success_gate: blocked" in rendered
    assert "repair_pressure_overloaded:12" in rendered
