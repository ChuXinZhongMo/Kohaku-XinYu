from __future__ import annotations

import json
from pathlib import Path

from xinyu_learning_closed_loop import (
    STYLE_REPAIR_SUCCESS_MARKERS,
    SUCCESS_CANCEL_MARKERS,
    SUCCESS_MARKERS,
    SUCCESS_REPLY_CONTEXT_MARKERS,
)
from xinyu_memory_health_report import build_memory_health_report, render_memory_health_report
from xinyu_stage8_learning_trial_validation_packet import (
    ACCEPTED_SUCCESS_DISPLAY_EXAMPLES,
    CANCEL_DISPLAY_EXAMPLES,
    REPLY_CONTEXT_DISPLAY_EXAMPLES,
    STYLE_SUCCESS_DISPLAY_EXAMPLES,
    build_stage8_learning_trial_validation_packet,
    render_stage8_learning_trial_validation_packet,
    write_stage8_learning_trial_validation_packet,
    write_stage8_learning_trial_validation_state,
)
from xinyu_text_variants import LEGACY_MOJIBAKE_FRAGMENTS


def _looks_mojibake(text: str) -> bool:
    if chr(0xFFFD) in text or "?" in text:
        return True
    if any(0xE000 <= ord(ch) <= 0xF8FF for ch in text):
        return True
    return any(fragment in text for fragment in LEGACY_MOJIBAKE_FRAGMENTS)


def _write_blocked_learning_state(root: Path, *, raw_private: str = "") -> None:
    path = root / "memory/self/learning_closed_loop_state.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# Learning Closed Loop State

## Current Loop
- status: trial_active
- updated_at: 2026-05-29T18:00:00+08:00
- latest_failure_kind: owner_reported_template_voice_failure
- active_trial_key: owner_reported_template_voice_failure
- active_trial_habit: 被指出模板味时，直接换成当前场景里的具体下一句，不写复盘和承诺。
- expected_next_behavior: 被指出模板味时，直接换成当前场景里的具体下一句，不写复盘和承诺。
- repair_count: 12
- success_count: 3
- success_streak: 0
- trial_success_count: 3
- trial_success_streak: 0
- promotion_signal: false
- last_owner_reaction: repair_pressure_overloaded

## Success Evidence
- latest_success_at: none
- latest_success_event_id: none
- latest_success_trial_key: none
- success_evidence_status: reset_by_failure
- success_evidence_ref: none
{raw_private}
""",
        encoding="utf-8",
    )


def test_stage8_learning_trial_validation_packet_reports_blocked_gate_without_private_text(tmp_path: Path) -> None:
    raw_private = "RAW_STAGE8_LEARNING_TRIAL_PRIVATE_TEXT_SHOULD_NOT_SURFACE_9201"
    _write_blocked_learning_state(tmp_path, raw_private=raw_private)
    trace_path = tmp_path / "runtime/learning_closed_loop_trace.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        json.dumps(
            {
                "event_id": "learnloop-test",
                "owner_private": True,
                "success": False,
                "failures": ["owner_reported_template_voice_failure"],
                "active_trial_key": "owner_reported_template_voice_failure",
                "success_evidence_status": "reset_by_failure",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    packet = build_stage8_learning_trial_validation_packet(tmp_path)
    rendered = render_stage8_learning_trial_validation_packet(packet)
    packet_path = write_stage8_learning_trial_validation_packet(tmp_path, packet)
    state_path = write_stage8_learning_trial_validation_state(tmp_path, packet, packet_path=packet_path)
    state = state_path.read_text(encoding="utf-8")

    assert packet["packet_status"] == "blocked_waiting_for_owner_success"
    assert packet["gate"]["learning_trial_success_gate"] == "blocked"
    assert packet["gate"]["needed_consecutive_success_count"] == 2
    assert "status_not_trial_supported:trial_active" in packet["gate"]["blockers"]
    assert "success_evidence_not_same_trial:reset_by_failure" in packet["gate"]["blockers"]

    # Phase C: owner-visible review packet for the blocked learning key.
    decision = packet["owner_review_decision"]
    assert decision["blocked_key"] == "owner_reported_template_voice_failure"
    # Owner is told what is still missing, not asked to approve a stable write.
    assert decision["owner_action"] == "collect_2_more_same_trial_explicit_owner_success"
    assert decision["source"].startswith("runtime_learning_closed_loop_trial:owner_reported_template_voice_failure")
    assert "raw_owner_text_excluded" in decision["source"]
    assert decision["reason"].startswith("blocked:")
    # No auto-promotion: stable memory stays blocked.
    assert "no_auto_promotion_to_stable_memory" in decision["boundary"]
    assert "stable_profile_write:blocked" in decision["boundary"]
    assert decision["required_success_signal"]["consecutive_same_trial_explicit_owner_success_required"] == 2
    assert decision["required_success_signal"]["still_needed"] == 2
    assert decision["required_success_signal"]["must_match_active_trial_key"] == "owner_reported_template_voice_failure"
    assert any("nothing_to_revert_at_stable_layer" in step for step in decision["rollback_path"])
    assert any("separate_explicit_owner_action" in step for step in decision["rollback_path"])
    assert "owner_action: collect_2_more_same_trial_explicit_owner_success" in state
    assert "- blocked_key: owner_reported_template_voice_failure" in state
    assert packet["latest_trace_summary"]["failure_kinds"] == ["owner_reported_template_voice_failure"]
    assert any("自然" in item for item in packet["success_capture_contract"]["accepted_success_marker_examples"])
    assert "这句" in packet["success_capture_contract"]["generic_success_requires_reply_context_markers"]
    assert "但是" in packet["success_capture_contract"]["cancel_markers_that_turn_success_into_failure"]
    assert "validation_status: blocked_waiting_for_owner_success" in state
    assert "needed_consecutive_success_count: 2" in state
    assert raw_private not in str(packet)
    assert raw_private not in rendered
    assert raw_private not in packet_path.read_text(encoding="utf-8")
    assert raw_private not in state
    assert "raw_owner_text_in_state: false" in state
    assert "stable_memory_write: blocked" in state


def test_validation_packet_contract_samples_are_display_clean(tmp_path: Path) -> None:
    _write_blocked_learning_state(tmp_path)
    packet = build_stage8_learning_trial_validation_packet(tmp_path)
    rendered = render_stage8_learning_trial_validation_packet(packet)
    contract = packet["success_capture_contract"]
    for key in (
        "accepted_success_marker_examples",
        "style_trial_success_examples",
        "generic_success_requires_reply_context_markers",
        "cancel_markers_that_turn_success_into_failure",
    ):
        for sample in contract[key]:
            assert not _looks_mojibake(sample), (key, sample)
    # Readable anchors are still present, so the filter did not over-prune.
    assert "自然多了" in contract["accepted_success_marker_examples"]
    assert "这句" in contract["generic_success_requires_reply_context_markers"]
    assert "但是" in contract["cancel_markers_that_turn_success_into_failure"]
    assert chr(0xFFFD) not in rendered


def test_validation_packet_display_examples_stay_real_matcher_members() -> None:
    # Display lists must remain a subset of the live matcher sets, so owner-facing
    # examples never drift from what is actually accepted.
    assert set(ACCEPTED_SUCCESS_DISPLAY_EXAMPLES) <= set(SUCCESS_MARKERS)
    assert set(STYLE_SUCCESS_DISPLAY_EXAMPLES) <= set(STYLE_REPAIR_SUCCESS_MARKERS)
    assert set(REPLY_CONTEXT_DISPLAY_EXAMPLES) <= set(SUCCESS_REPLY_CONTEXT_MARKERS)
    assert set(CANCEL_DISPLAY_EXAMPLES) <= set(SUCCESS_CANCEL_MARKERS)
    # And none of the curated examples are themselves mojibake.
    for example in (
        *ACCEPTED_SUCCESS_DISPLAY_EXAMPLES,
        *STYLE_SUCCESS_DISPLAY_EXAMPLES,
        *REPLY_CONTEXT_DISPLAY_EXAMPLES,
        *CANCEL_DISPLAY_EXAMPLES,
    ):
        assert not _looks_mojibake(example), example


def test_stage8_learning_trial_validation_packet_reports_satisfied_gate(tmp_path: Path) -> None:
    path = tmp_path / "memory/self/learning_closed_loop_state.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# Learning Closed Loop State

## Current Loop
- status: trial_supported
- latest_failure_kind: owner_reported_template_voice_failure
- active_trial_key: owner_reported_template_voice_failure
- active_trial_habit: direct replacement line, no feedback-processing phrase
- expected_next_behavior: change the next visible line without a repair report
- repair_count: 1
- success_count: 2
- success_streak: 2
- trial_success_count: 2
- trial_success_streak: 2
- promotion_signal: possible_after_self_review
- last_owner_reaction: explicit_success

## Success Evidence
- latest_success_at: 2026-05-29T18:05:00+08:00
- latest_success_trial_key: owner_reported_template_voice_failure
- success_evidence_status: same_trial_explicit_owner_success
""",
        encoding="utf-8",
    )

    packet = build_stage8_learning_trial_validation_packet(tmp_path)

    assert packet["packet_status"] == "satisfied"
    assert packet["gate"]["learning_trial_success_gate"] == "satisfied"
    assert packet["gate"]["needed_consecutive_success_count"] == 0
    assert packet["gate"]["blockers"] == []
    # Even when the success gate is satisfied, promotion still requires an explicit owner apply.
    decision = packet["owner_review_decision"]
    assert decision["owner_action"] == "owner_explicit_apply_required_no_auto_promotion"
    assert decision["required_success_signal"]["still_needed"] == 0
    assert "no_auto_promotion_to_stable_memory" in decision["boundary"]


def test_memory_health_report_tracks_learning_trial_validation_packet(tmp_path: Path) -> None:
    _write_blocked_learning_state(tmp_path)

    missing = build_memory_health_report(tmp_path)
    assert missing["learning_trial_validation"]["learning_trial_validation_status"] == "missing"
    assert "write_or_refresh_stage8_learning_trial_validation_packet" in missing["recommendations"]

    packet = build_stage8_learning_trial_validation_packet(tmp_path)
    packet_path = write_stage8_learning_trial_validation_packet(tmp_path, packet)
    write_stage8_learning_trial_validation_state(tmp_path, packet, packet_path=packet_path)

    ready = build_memory_health_report(tmp_path)
    rendered = render_memory_health_report(ready)
    stage8 = ready["stage8_memory_governance"]

    assert ready["learning_trial_validation"]["learning_trial_validation_status"] == "blocked_waiting_for_owner_success"
    assert stage8["learning_trial_validation_status"] == "blocked_waiting_for_owner_success"
    assert stage8["learning_trial_validation_needed_success_count"] == 2
    # Owner-action surfaces through the governance dict that xinyu_status.py renders.
    assert stage8["learning_trial_validation_owner_action"] == "collect_2_more_same_trial_explicit_owner_success"
    assert "learning_trial_validation_status: blocked_waiting_for_owner_success" in rendered
    assert "learning_trial_validation_owner_action: collect_2_more_same_trial_explicit_owner_success" in rendered
