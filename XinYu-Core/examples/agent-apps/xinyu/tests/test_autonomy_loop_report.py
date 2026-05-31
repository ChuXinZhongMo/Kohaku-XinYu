from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from xinyu_autonomy_loop_report import build_autonomy_loop_report, render_autonomy_loop_report


NOW = datetime(2026, 5, 27, 6, 45, tzinfo=timezone.utc)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _status() -> dict:
    return {
        "ok": True,
        "checks": [
            {"name": "core_bridge", "ok": True, "detail": "running"},
            {"name": "xinyu_qq_gateway_6199", "ok": True, "detail": "tcp connect"},
            {"name": "napcat_to_xinyu_qq_gateway_ws", "ok": True, "detail": "established"},
        ],
        "core": {"known_error_count": 0},
    }


def _seed_live_loop(root: Path) -> None:
    runtime = root / "runtime"
    _write_jsonl(
        runtime / "qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "queued",
                "recorded_at": "2026-05-27T14:40:00+08:00",
            },
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "dispatch_start",
                "recorded_at": "2026-05-27T14:40:05+08:00",
            },
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "11110000",
                "stage": "reply_sent",
                "recorded_at": "2026-05-27T14:40:20+08:00",
            },
        ],
    )
    _write_jsonl(
        runtime / "answer_discipline_visible_send_shadow.jsonl",
        [
            {
                "source": "direct_chat_pre_send",
                "target_kind": "private",
                "passed": True,
                "shadow_only": True,
                "raw_prompt_saved": False,
                "raw_reply_saved": False,
                "observed_at": "2026-05-27T14:40:19+08:00",
            }
        ],
    )
    _write_jsonl(
        runtime / "gateway_ack_spool.jsonl",
        [
            {
                "event": "pending",
                "key": "adapter|22220000|chat",
                "created_at": "2026-05-27T14:40:20+08:00",
                "payload": {
                    "route": "chat",
                    "adapter_message_id": "22220000",
                    "source_message_id": "11110000",
                    "visible_text": "must not leak",
                },
            },
            {
                "event": "acked",
                "key": "adapter|22220000|chat",
                "acked_at": "2026-05-27T14:40:21+08:00",
                "adapter_message_id": "22220000",
                "route": "chat",
            },
        ],
    )
    _write_jsonl(
        runtime / "dialogue_working_memory/session.jsonl",
        [
            {
                "role": "assistant",
                "content": "must not leak",
                "recorded_at": "2026-05-27T14:40:20+08:00",
            }
        ],
    )


def _seed_silence_live_loop(root: Path) -> None:
    runtime = root / "runtime"
    _write_jsonl(
        runtime / "qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "silence-input",
                "stage": "queued",
                "recorded_at": "2026-05-27T14:40:00+08:00",
            },
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "silence-input",
                "stage": "dispatch_start",
                "recorded_at": "2026-05-27T14:40:05+08:00",
            },
        ],
    )


def _seed_states(root: Path) -> None:
    context = root / "memory/context"
    context.mkdir(parents=True, exist_ok=True)
    (context / "intention_ecology_state.md").write_text(
        """
- selected_intent: answer_current_turn
- selected_gate: current_turn_only
- action_level: visible_reply_only
- autonomy_posture: current_turn_grounded_choice
- feedback_signal: owner_feedback
- action_feedback_signal: qq_visible_reply_ack
- action_feedback_bias: route_confirmed_visible_reply_risk:-4
- perception_gap_signal: owner_attention
- perception_gap_bias: owner_attention_current_turn_value:+6;require_short_term_anchor
- perception_route_hint: attention_posture_and_intention_ecology
- proactive_candidate: none
- memory_candidate: current_turn_only
- restraint_reason: none
- candidate_count: 1
- candidate_competition_status: observed
- selected_total_score: 52
- runner_up_intent: none
- runner_up_gate: none
- runner_up_total_score: 0
- score_margin: 52
- blocked_candidate_count: 0
- held_candidate_count: 0
- review_gated_future_count: 0
- competition_reason: selected=answer_current_turn; no_runner_up
- runner_up_not_selected_reason: no_runner_up_to_compare
- gate_pressure_summary: selected_gate=current_turn_only; runner_up_gate=none; blocked=0; held=0; review_gated=0
- blocked_intents: none
- held_intents: none
- review_gated_intents: none
- proactive_delivery: review_gated
- stable_memory_write: gated
- raw_private_body_retained: false
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (context / "action_feedback_state.md").write_text(
        """
- status: active
- checked_at: 2026-05-27T14:40:21+08:00
- event_id: actfb-test
- feedback_signal: qq_visible_reply_ack
- feedback_source: internal_message_ack
- action_result: delivered
- route: chat
- target_kind: private
- future_effect: confirm_visible_reply_transport_for_next_turn
- scoring_effect: keep_current_route_available
- memory_effect: sent_reply_index_updated
- raw_private_body_retained: false
- visible_reply_text_retained: false
- stable_memory_write: blocked
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (context / "attention_posture_state.md").write_text(
        """
- attention_target: owner_private
- attention_mode: available
- ignored_event_count: 0
- noted_event_count: 1
- last_route: current_turn
- perception_gap_type: owner_attention
- perception_route_hint: attention_posture_and_intention_ecology
- perception_gap_consumed: true
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _seed_silence_states(root: Path, *, restraint_reason: str = "owner_needs_space") -> None:
    context = root / "memory/context"
    context.mkdir(parents=True, exist_ok=True)
    (context / "intention_ecology_state.md").write_text(
        f"""
- selected_intent: hold_presence
- selected_gate: hold_or_silence
- action_level: visible_reply_only
- autonomy_posture: bounded_restraint
- feedback_signal: none
- perception_gap_signal: owner_attention
- perception_gap_bias: owner_attention_current_turn_value:+6;require_short_term_anchor
- perception_route_hint: attention_posture_and_intention_ecology
- proactive_candidate: none
- memory_candidate: none
- restraint_reason: {restraint_reason}
- candidate_count: 2
- candidate_competition_status: observed
- selected_total_score: 44
- runner_up_intent: answer_current_turn
- runner_up_gate: current_turn_only
- runner_up_total_score: 28
- score_margin: 16
- blocked_candidate_count: 0
- held_candidate_count: 1
- review_gated_future_count: 0
- competition_reason: selected=hold_presence; runner_up=answer_current_turn; margin=16
- runner_up_not_selected_reason: lower_total_score:margin=16
- gate_pressure_summary: selected_gate=hold_or_silence; runner_up_gate=current_turn_only; blocked=0; held=1; review_gated=0
- blocked_intents: none
- held_intents: hold_presence
- review_gated_intents: none
- proactive_delivery: review_gated
- stable_memory_write: gated
- raw_private_body_retained: false
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (context / "attention_posture_state.md").write_text(
        """
- attention_target: owner_private
- attention_mode: hold_quietly
- ignored_event_count: 0
- noted_event_count: 1
- last_route: current_turn
- perception_gap_type: owner_attention
- perception_route_hint: attention_posture_and_intention_ecology
- perception_gap_consumed: true
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _seed_local_action_states(root: Path) -> None:
    context = root / "memory/context"
    context.mkdir(parents=True, exist_ok=True)
    (context / "intention_ecology_state.md").write_text(
        """
- selected_intent: do_bounded_task
- selected_gate: current_turn_only
- action_level: visible_reply_or_local_work
- autonomy_posture: bounded_local_work
- feedback_signal: none
- action_feedback_signal: none
- action_feedback_bias: none
- action_feedback_coverage_signal: patch_task_prepared
- action_feedback_coverage_bias: patch_task_prepared_task_risk:-2
- perception_gap_signal: owner_attention
- perception_gap_bias: owner_attention_current_turn_value:+6;require_short_term_anchor
- perception_route_hint: attention_posture_and_intention_ecology
- proactive_candidate: none
- memory_candidate: none
- restraint_reason: none
- candidate_count: 2
- candidate_competition_status: observed
- selected_total_score: 88
- runner_up_intent: answer_current_turn
- runner_up_gate: current_turn_only
- runner_up_total_score: 36
- score_margin: 52
- blocked_candidate_count: 0
- held_candidate_count: 0
- review_gated_future_count: 0
- competition_reason: selected=do_bounded_task; runner_up=answer_current_turn; margin=52
- runner_up_not_selected_reason: lower_total_score:margin=52
- gate_pressure_summary: selected_gate=current_turn_only; runner_up_gate=current_turn_only; blocked=0; held=0; review_gated=0
- blocked_intents: none
- held_intents: none
- review_gated_intents: none
- proactive_delivery: review_gated
- stable_memory_write: gated
- raw_private_body_retained: false
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (context / "attention_posture_state.md").write_text(
        """
- attention_target: local_task
- attention_mode: repair_needed
- ignored_event_count: 0
- noted_event_count: 1
- last_route: local_action
- perception_gap_type: owner_attention
- perception_route_hint: attention_posture_and_intention_ecology
- perception_gap_consumed: true
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (context / "self_action_patch_executor_state.md").write_text(
        """
- checked_at: 2026-05-27T14:41:00+08:00
- status: prepared
- execution_level: prepare
- queue_id: selfaction-queue-test
- task_id: selfaction-patch-test
- codex_status: not_requested
- report_path: none
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _seed_short_term_continuity(root: Path, *, recall_status: str = "tail_available") -> None:
    context = root / "memory/context"
    context.mkdir(parents=True, exist_ok=True)
    tail_count = "4" if recall_status == "tail_available" else "0"
    recent_user_count = "2" if recall_status == "tail_available" else "0"
    recent_assistant_count = "2" if recall_status == "tail_available" else "0"
    (context / "short_term_continuity_state.md").write_text(
        f"""
- status: active
- direct_reference: true
- recall_status: {recall_status}
- recall_source: dialogue_tail
- tail_count: {tail_count}
- archive_recovered_count: 0
- recent_user_count: {recent_user_count}
- recent_assistant_count: {recent_assistant_count}
- latest_user_ref: sha256:userhash
- latest_assistant_ref: sha256:assistanthash
- raw_private_body_retained: false
- visible_reply_text_retained: false
RAW_OWNER_PRIVATE_LINE_SHOULD_NOT_RENDER_7194
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _seed_learning_owner_feedback(root: Path) -> None:
    state_path = root / "memory/self/learning_closed_loop_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Learning Closed Loop State

## Current Loop
- status: trial_active
- updated_at: 2026-05-27T14:42:00+08:00
- latest_event_id: learnloop-owner-effect
- latest_failure_kind: owner_reported_template_voice_failure
- active_trial_habit: direct replacement line, no feedback-processing phrase
- expected_next_behavior: change the next visible line without a repair report
- repair_count: 1
- success_count: 0
- success_streak: 0
- promotion_signal: false
- last_owner_reaction: repair_pressure
RAW_OWNER_FEEDBACK_EFFECT_SHOULD_NOT_RENDER_8241
""",
        encoding="utf-8",
    )


def _seed_overloaded_learning_owner_feedback(root: Path) -> None:
    state_path = root / "memory/self/learning_closed_loop_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Learning Closed Loop State

## Current Loop
- status: trial_active
- updated_at: 2026-05-27T14:42:00+08:00
- latest_event_id: learnloop-owner-effect
- latest_failure_kind: owner_reported_template_voice_failure
- active_trial_key: owner_reported_template_voice_failure
- active_trial_habit: direct replacement line, no feedback-processing phrase
- expected_next_behavior: change the next visible line without a repair report
- repair_count: 94
- success_count: 3
- success_streak: 0
- trial_success_count: 3
- trial_success_streak: 0
- latest_success_trial_key: none
- success_evidence_status: none
- promotion_signal: false
- last_owner_reaction: repair_pressure
""",
        encoding="utf-8",
    )


def _seed_desktop_owner_response(root: Path) -> None:
    state_path = root / "memory/context/proactive_request_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Proactive Request State

- status: approved
- checked_at: 2026-05-27T14:42:00+08:00
- request_id: proactive-response-test
- request_answer_state: approved_qq
- last_ack_status: approved_qq
- requested_action: ask_owner
RAW_DESKTOP_OWNER_RESPONSE_SHOULD_NOT_RENDER_3138
""",
        encoding="utf-8",
    )


def test_autonomy_loop_report_passes_for_verified_closed_loop(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)
    output = render_autonomy_loop_report(report)

    assert report["ok"] is True
    assert "visible_reply_sent_and_qq_ack_observed" in output
    assert "intention_feedback_bias=route_confirmed_visible_reply_risk:-4" in output
    assert "must not leak" not in output
    assert report["privacy"]["consciousness_claim"] is False
    assert report["state"]["qq_reply_integrity_diagnostics"]["status"] == "pass"
    assert report["state"]["qq_reply_integrity_diagnostics"]["visible_chat_reply_count"] == 1
    assert report["state"]["decision_chain"]["selected_total_score"] == "52"
    assert report["state"]["decision_chain"]["score_margin"] == "52"
    assert report["state"]["decision_chain"]["runner_up_not_selected_reason"] == "no_runner_up_to_compare"
    assert report["state"]["decision_chain"]["gate_pressure_summary"].startswith("selected_gate=current_turn_only")
    assert any(
        check["name"] == "qq_reply_integrity_diagnostics"
        and check["ok"]
        and check["required"]
        and "visible=1" in check["detail"]
        for check in report["checks"]
    )
    assert any(
        check["name"] == "candidate_competition_auditable"
        and check["ok"]
        and check["required"]
        and "selected_score=52" in check["detail"]
        and "runner_up_reason=no_runner_up_to_compare" in check["detail"]
        for check in report["checks"]
    )
    assert report["state"]["decision_chain"]["perception_internal_consumed"] == "true"
    assert any(
        check["name"] == "perception_gap_consumed_by_internal_state"
        and check["ok"]
        and check["required"]
        and "gap=owner_attention" in check["detail"]
        for check in report["checks"]
    )


def test_autonomy_loop_report_accepts_explained_silence_without_visible_ack(tmp_path: Path) -> None:
    _seed_silence_live_loop(tmp_path)
    _seed_silence_states(tmp_path, restraint_reason="owner_needs_space")

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)
    output = render_autonomy_loop_report(report)

    assert report["ok"] is True
    assert report["state"]["decision_chain"]["action_result"] == "bounded_non_action:hold_or_silence"
    assert report["state"]["decision_chain"]["restraint_reason"] == "owner_needs_space"
    assert any(
        check["name"] == "silence_or_hold_explained"
        and check["ok"]
        and check["required"]
        and "restraint_reason=owner_needs_space" in check["detail"]
        for check in report["checks"]
    )
    assert any(
        check["name"] == "feedback_changes_future_surface"
        and check["ok"]
        and not check["required"]
        for check in report["checks"]
    )
    assert "decision_chain" in output


def test_autonomy_loop_report_accepts_local_action_evidence_without_visible_ack(tmp_path: Path) -> None:
    _seed_silence_live_loop(tmp_path)
    _seed_local_action_states(tmp_path)

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is True
    assert report["state"]["decision_chain"]["action_result"] == (
        "local_action_result_observed:patch_executor/patch_task_prepared/prepared"
    )
    assert report["state"]["decision_chain"]["action_evidence_surface"] == "patch_executor"
    assert report["state"]["decision_chain"]["action_evidence_signal"] == "patch_task_prepared"
    assert report["state"]["decision_chain"]["action_evidence_lifecycle"] == "prepared"
    assert report["state"]["decision_chain"]["next_behavior_bias"] == "patch_task_prepared_task_risk:-2"
    assert report["state"]["decision_chain"]["feedback_consumption_status"] == "consumed"
    assert "action_feedback_coverage:patch_task_prepared/prepared" in (
        report["state"]["decision_chain"]["feedback_consumed_sources"]
    )
    assert "action_feedback_coverage_bias:patch_task_prepared_task_risk:-2" in (
        report["state"]["decision_chain"]["feedback_consumed_biases"]
    )
    assert any(
        check["name"] == "truthful_action_result"
        and check["ok"]
        and "patch_executor/patch_task_prepared/prepared" in check["detail"]
        for check in report["checks"]
    )
    assert any(
        check["name"] == "visible_send_privacy_guard"
        and check["ok"]
        and not check["required"]
        and "not_required_for_gate=current_turn_only/action_level=visible_reply_or_local_work" in check["detail"]
        for check in report["checks"]
    )
    assert any(
        check["name"] == "feedback_changes_future_surface"
        and check["ok"]
        and "coverage_feedback=true" in check["detail"]
        for check in report["checks"]
    )
    assert any(
        check["name"] == "feedback_consumption_auditable"
        and check["ok"]
        and check["required"]
        and "sources=action_feedback_coverage:patch_task_prepared/prepared" in check["detail"]
        for check in report["checks"]
    )


def test_autonomy_loop_report_requires_reason_for_silence_or_hold(tmp_path: Path) -> None:
    _seed_silence_live_loop(tmp_path)
    _seed_silence_states(tmp_path, restraint_reason="none")

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    assert any(
        check["name"] == "silence_or_hold_explained"
        and not check["ok"]
        and check["required"]
        and "restraint_reason=none" in check["detail"]
        for check in report["checks"]
    )


def test_autonomy_loop_report_surfaces_short_term_continuity_anchor(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    _seed_short_term_continuity(tmp_path, recall_status="tail_available")

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)
    output = render_autonomy_loop_report(report)

    assert report["ok"] is True
    assert report["state"]["short_term_continuity"]["direct_reference"] == "true"
    assert report["state"]["short_term_continuity"]["recall_status"] == "tail_available"
    assert report["state"]["short_term_continuity"]["recall_source"] == "dialogue_tail"
    assert any(
        check["name"] == "short_term_continuity_anchor_visible"
        and check["ok"]
        and check["required"]
        and "recall_status=tail_available" in check["detail"]
        and "recall_source=dialogue_tail" in check["detail"]
        for check in report["checks"]
    )
    assert "RAW_OWNER_PRIVATE_LINE_SHOULD_NOT_RENDER_7194" not in output


def test_autonomy_loop_report_requires_tail_when_direct_reference_was_requested(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    _seed_short_term_continuity(tmp_path, recall_status="tail_missing")

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    assert any(
        check["name"] == "short_term_continuity_anchor_visible"
        and not check["ok"]
        and check["required"]
        and "recall_status=tail_missing" in check["detail"]
        for check in report["checks"]
    )


def test_autonomy_loop_report_fails_without_gate_state(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    (tmp_path / "memory/context").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory/context/intention_ecology_state.md").write_text(
        "- selected_intent: answer_current_turn\n",
        encoding="utf-8",
    )

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    assert any(check["name"] == "gate_decision_visible" and not check["ok"] for check in report["checks"])


def test_autonomy_loop_report_does_not_use_old_stale_drop_for_new_input(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    _write_jsonl(
        runtime / "qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "old",
                "stage": "stale_reply_dropped",
                "recorded_at": "2026-05-27T14:30:00+08:00",
                "drop_reason": "newer_input_before_visible_send:1->2",
            },
            {
                "arrival_seq": 2,
                "message_kind": "private",
                "message_id": "new",
                "stage": "queued",
                "recorded_at": "2026-05-27T14:40:00+08:00",
            },
            {
                "arrival_seq": 2,
                "message_kind": "private",
                "message_id": "new",
                "stage": "dispatch_start",
                "recorded_at": "2026-05-27T14:40:05+08:00",
            },
        ],
    )
    _write_jsonl(
        runtime / "answer_discipline_visible_send_shadow.jsonl",
        [
            {
                "source": "direct_chat_pre_send",
                "target_kind": "private",
                "passed": True,
                "shadow_only": True,
                "raw_prompt_saved": False,
                "raw_reply_saved": False,
                "observed_at": "2026-05-27T14:40:06+08:00",
            }
        ],
    )
    _seed_states(tmp_path)

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    assert any(
        check["name"] == "truthful_action_result"
        and not check["ok"]
        and "older_than_latest" in check["detail"]
        for check in report["checks"]
    )


def test_autonomy_loop_report_requires_feedback_future_surface(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    (tmp_path / "memory/context/action_feedback_state.md").unlink()

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    assert any(
        check["name"] == "feedback_changes_future_surface"
        and not check["ok"]
        and "feedback_signal=missing" in check["detail"]
        for check in report["checks"]
    )


def test_autonomy_loop_report_requires_intention_ecology_feedback_bias(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    intention_path = tmp_path / "memory/context/intention_ecology_state.md"
    intention_path.write_text(
        intention_path.read_text(encoding="utf-8").replace(
            "- action_feedback_bias: route_confirmed_visible_reply_risk:-4\n",
            "- action_feedback_bias: none\n",
        ),
        encoding="utf-8",
    )

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    assert any(
        check["name"] == "feedback_changes_future_surface"
        and not check["ok"]
        and "intention_feedback_bias=none" in check["detail"]
        for check in report["checks"]
    )


def test_autonomy_loop_report_surfaces_multi_action_feedback_coverage(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    codex_path = tmp_path / "runtime/codex_presence_state.json"
    codex_path.parent.mkdir(parents=True, exist_ok=True)
    codex_path.write_text(
        json.dumps(
            {
                "updated_at": "2026-05-27T14:41:00+08:00",
                "status": "finished",
                "job_id": "codex-job-coverage",
                "exit_code": 0,
                "timed_out": False,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    intention_path = tmp_path / "memory/context/intention_ecology_state.md"
    intention_path.write_text(
        intention_path.read_text(encoding="utf-8")
        + "- action_feedback_coverage_signal: codex_delegate_finished\n"
        + "- action_feedback_coverage_bias: codex_delegate_finished_task_risk:-2\n",
        encoding="utf-8",
    )

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)
    output = render_autonomy_loop_report(report)

    assert report["ok"] is True
    assert report["state"]["action_feedback_coverage"]["status"] == "pass"
    assert report["state"]["action_feedback_coverage"]["non_qq_surface_count"] == 1
    assert any(
        check["name"] == "multi_action_feedback_coverage"
        and check["ok"]
        and check["required"]
        and "non_qq=1" in check["detail"]
        for check in report["checks"]
    )
    assert any(
        check["name"] == "multi_action_feedback_consumed_by_intention"
        and check["ok"]
        and check["required"]
        and "coverage_signal=codex_delegate_finished" in check["detail"]
        for check in report["checks"]
    )
    assert "action_feedback_coverage" in output


def test_autonomy_loop_report_requires_coverage_feedback_consumption_when_non_qq_observed(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    codex_path = tmp_path / "runtime/codex_presence_state.json"
    codex_path.parent.mkdir(parents=True, exist_ok=True)
    codex_path.write_text(
        json.dumps(
            {
                "updated_at": "2026-05-27T14:41:00+08:00",
                "status": "finished",
                "job_id": "codex-job-coverage",
                "exit_code": 0,
                "timed_out": False,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    assert any(
        check["name"] == "multi_action_feedback_consumed_by_intention"
        and not check["ok"]
        and check["required"]
        and "coverage_bias=missing" in check["detail"]
        for check in report["checks"]
    )


def test_autonomy_loop_report_surfaces_owner_feedback_effect_consumption(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    _seed_learning_owner_feedback(tmp_path)
    intention_path = tmp_path / "memory/context/intention_ecology_state.md"
    intention_path.write_text(
        intention_path.read_text(encoding="utf-8")
        + "- owner_feedback_effect_signal: owner_reported_template_voice_failure\n"
        + "- owner_feedback_effect_bias: repair_relation_visible_risk:-6\n"
        + "- owner_feedback_expression_bias: avoid_template_or_feedback_processing_phrase\n",
        encoding="utf-8",
    )

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)
    output = render_autonomy_loop_report(report)

    assert report["ok"] is True
    assert report["state"]["owner_feedback_effect"]["status"] == "active"
    assert report["state"]["owner_feedback_effect"]["latest_feedback_kind"] == "owner_reported_template_voice_failure"
    assert any(
        check["name"] == "owner_feedback_changes_expression_strategy"
        and check["ok"]
        and check["required"]
        and "intention_bias=repair_relation_visible_risk:-6" in check["detail"]
        for check in report["checks"]
    )
    assert "RAW_OWNER_FEEDBACK_EFFECT_SHOULD_NOT_RENDER_8241" not in output


def test_autonomy_loop_report_requires_owner_feedback_effect_consumption(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    _seed_learning_owner_feedback(tmp_path)

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    assert any(
        check["name"] == "owner_feedback_changes_expression_strategy"
        and not check["ok"]
        and check["required"]
        and "intention_signal=missing" in check["detail"]
        for check in report["checks"]
    )


def test_autonomy_loop_report_accepts_direct_only_owner_feedback_cooldown(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    _seed_overloaded_learning_owner_feedback(tmp_path)
    intention_path = tmp_path / "memory/context/intention_ecology_state.md"
    intention_path.write_text(
        intention_path.read_text(encoding="utf-8")
        + "- owner_feedback_effect_signal: none\n"
        + "- owner_feedback_effect_bias: none\n"
        + "- owner_feedback_expression_bias: none\n"
        + "- notes: owner_feedback_effect_cooldown:direct_failure_only\n",
        encoding="utf-8",
    )

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is True
    assert any(
        check["name"] == "owner_feedback_changes_expression_strategy"
        and check["ok"]
        and check["required"]
        and "realtime_pressure=capped_direct_failure_only" in check["detail"]
        for check in report["checks"]
    )


def test_autonomy_loop_report_surfaces_owner_response_feedback_consumption(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    _seed_desktop_owner_response(tmp_path)
    intention_path = tmp_path / "memory/context/intention_ecology_state.md"
    intention_path.write_text(
        intention_path.read_text(encoding="utf-8")
        + "- action_feedback_coverage_signal: desktop_approved_qq\n"
        + "- action_feedback_coverage_bias: desktop_feedback_updates_request_strategy\n"
        + "- owner_response_feedback_signal: desktop_approved_qq\n"
        + "- owner_response_feedback_bias: one_time_qq_permission:+8\n"
        + "- owner_response_strategy_bias: allow_one_bounded_qq_enqueue_if_gates_pass\n",
        encoding="utf-8",
    )

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)
    output = render_autonomy_loop_report(report)

    assert report["ok"] is True
    assert report["state"]["owner_feedback_effect"]["owner_response_signal"] == "desktop_approved_qq"
    assert any(
        check["name"] == "owner_response_changes_request_strategy"
        and check["ok"]
        and check["required"]
        and "intention_bias=one_time_qq_permission:+8" in check["detail"]
        for check in report["checks"]
    )
    assert "RAW_DESKTOP_OWNER_RESPONSE_SHOULD_NOT_RENDER_3138" not in output


def test_autonomy_loop_report_requires_owner_response_feedback_consumption(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    _seed_desktop_owner_response(tmp_path)
    intention_path = tmp_path / "memory/context/intention_ecology_state.md"
    intention_path.write_text(
        intention_path.read_text(encoding="utf-8")
        + "- action_feedback_coverage_signal: desktop_approved_qq\n"
        + "- action_feedback_coverage_bias: desktop_feedback_updates_request_strategy\n",
        encoding="utf-8",
    )

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    assert any(
        check["name"] == "owner_response_changes_request_strategy"
        and not check["ok"]
        and check["required"]
        and "intention_signal=missing" in check["detail"]
        for check in report["checks"]
    )


def test_autonomy_loop_report_requires_canary_pass_when_direct_reference_samples_exist(tmp_path: Path) -> None:
    private_reply = "\u4f60\u6307\u54ea\u4e00\u53e5\uff1f"
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    _write_jsonl(
        tmp_path / "runtime/short_term_continuity_trace.jsonl",
        [
            {
                "checked_at": "2026-05-27T14:40:10+08:00",
                "turn_id": "turn-canary-bad",
                "status": "active",
                "direct_reference": True,
                "recall_status": "tail_available",
                "recall_source": "dialogue_tail",
                "tail_count": 4,
                "archive_recovered_count": 0,
                "recent_user_count": 2,
                "recent_assistant_count": 2,
                "latest_user_ref": "sha256:userhash",
                "latest_assistant_ref": "sha256:assistanthash",
                "raw_private_body_retained": False,
                "visible_reply_text_retained": False,
            }
        ],
    )
    ack_path = tmp_path / "runtime/gateway_ack_spool.jsonl"
    with ack_path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(
            json.dumps(
                {
                    "event": "pending",
                    "key": "adapter|turn-canary-bad|chat",
                    "created_at": "2026-05-27T14:40:20+08:00",
                    "payload": {
                        "route": "chat",
                        "turn_id": "turn-canary-bad",
                        "source_message_id": "11110000",
                        "sent_at": "2026-05-27T14:40:20+08:00",
                        "visible_text": private_reply,
                    },
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)
    output = render_autonomy_loop_report(report)

    assert report["ok"] is False
    assert report["state"]["short_term_continuity_canary"]["status"] == "needs_check"
    assert report["state"]["short_term_continuity_canary"]["which_sentence_recurrence_count"] == 1
    assert any(
        check["name"] == "short_term_continuity_canary"
        and not check["ok"]
        and check["required"]
        and "which_sentence_recurrence_count=1" in check["detail"]
        for check in report["checks"]
    )
    assert private_reply not in output


def test_autonomy_loop_report_requires_recall_diagnostics_pass_for_direct_reference(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    _write_jsonl(
        tmp_path / "runtime/short_term_continuity_trace.jsonl",
        [
            {
                "checked_at": "2026-05-27T14:40:10+08:00",
                "turn_id": "turn-recall-diag-bad",
                "status": "active",
                "direct_reference": True,
                "recall_status": "tail_missing",
                "recall_source": "none",
                "tail_count": 0,
                "archive_recovered_count": 0,
                "recent_user_count": 0,
                "recent_assistant_count": 0,
                "latest_user_ref": "none",
                "latest_assistant_ref": "none",
                "notes": ["direct_reference_requested", "archive_fallback_no_payload", "recent_tail_missing"],
                "raw_private_body_retained": False,
                "visible_reply_text_retained": False,
            }
        ],
    )
    prompt_path = tmp_path / "runtime/prompt_pressure/last_live_prompt_pressure.json"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(
        json.dumps(
            {
                "turn_id": "turn-recall-diag-bad",
                "admitted_sidecars": [
                    {
                        "name": "short_term_continuity",
                        "admission": "current_turn",
                        "required": True,
                        "char_count": 900,
                        "reason": "required",
                    }
                ],
                "blocked_sidecars": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    assert report["state"]["short_term_recall_diagnostics"]["status"] == "needs_check"
    assert report["state"]["short_term_recall_diagnostics"]["primary_failure_class"] == "read_path"
    assert any(
        check["name"] == "short_term_recall_diagnostics"
        and not check["ok"]
        and check["required"]
        and "failure=read_path" in check["detail"]
        for check in report["checks"]
    )


def test_autonomy_loop_report_requires_qq_reply_integrity_for_visible_reply(tmp_path: Path) -> None:
    _seed_live_loop(tmp_path)
    _seed_states(tmp_path)
    _write_jsonl(
        tmp_path / "runtime/dialogue_working_memory/session.jsonl",
        [
            {
                "role": "assistant",
                "content": "different reply",
                "recorded_at": "2026-05-27T14:40:20+08:00",
            }
        ],
    )

    report = build_autonomy_loop_report(tmp_path, status_data=_status(), now=NOW)

    assert report["ok"] is False
    assert report["state"]["qq_reply_integrity_diagnostics"]["status"] == "needs_check"
    assert report["state"]["qq_reply_integrity_diagnostics"]["visible_reply_missing_working_memory_count"] == 1
    assert any(
        check["name"] == "qq_reply_integrity_diagnostics"
        and not check["ok"]
        and check["required"]
        and "missing_working_memory=1" in check["detail"]
        for check in report["checks"]
    )
