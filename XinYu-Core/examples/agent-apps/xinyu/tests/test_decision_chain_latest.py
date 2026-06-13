from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from xinyu_decision_chain_latest import (
    build_decision_chain_latest_report,
    render_decision_chain_latest_report,
    write_decision_chain_latest,
)
from xinyu_decision_chain_latest_store import decision_chain_latest_report_path
from xinyu_decision_chain_latest_store import decision_chain_latest_state_path


NOW = datetime(2026, 5, 27, 6, 45, tzinfo=timezone.utc)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _seed_visible_loop(root: Path, raw_reply: str) -> None:
    runtime = root / "runtime"
    _write_jsonl(
        runtime / "qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "decision-chain-input",
                "stage": "queued",
                "recorded_at": "2026-05-27T14:40:00+08:00",
            },
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "decision-chain-input",
                "stage": "dispatch_start",
                "recorded_at": "2026-05-27T14:40:05+08:00",
            },
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "decision-chain-input",
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
                "key": "adapter|decision-chain-output|chat",
                "created_at": "2026-05-27T14:40:20+08:00",
                "payload": {
                    "route": "chat",
                    "adapter_message_id": "decision-chain-output",
                    "source_message_id": "decision-chain-input",
                    "message_type": "private",
                    "visible_text": raw_reply,
                },
            },
            {
                "event": "acked",
                "key": "adapter|decision-chain-output|chat",
                "acked_at": "2026-05-27T14:40:21+08:00",
                "adapter_message_id": "decision-chain-output",
                "route": "chat",
            },
        ],
    )


def _seed_dispatch_only_loop(root: Path) -> None:
    _write_jsonl(
        root / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "decision-chain-local-action",
                "stage": "queued",
                "recorded_at": "2026-05-27T14:40:00+08:00",
            },
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "decision-chain-local-action",
                "stage": "dispatch_start",
                "recorded_at": "2026-05-27T14:40:05+08:00",
            },
        ],
    )


def _seed_common_states(root: Path, raw_private: str) -> None:
    context = root / "memory/context"
    context.mkdir(parents=True, exist_ok=True)
    (context / "intention_ecology_state.md").write_text(
        f"""
- selected_intent: answer_current_turn
- selected_gate: current_turn_only
- action_level: visible_reply_only
- autonomy_posture: current_turn_grounded_choice
- feedback_signal: owner_feedback
- action_feedback_signal: qq_visible_reply_ack
- action_feedback_bias: route_confirmed_visible_reply_risk:-4
- owner_feedback_effect_signal: owner_reported_template_voice_failure
- owner_feedback_effect_bias: repair_relation_visible_risk:-6
- owner_feedback_expression_bias: avoid_template_or_feedback_processing_phrase
- perception_gap_signal: owner_attention
- perception_gap_bias: owner_attention_current_turn_value:+6;require_short_term_anchor
- perception_route_hint: attention_posture_and_intention_ecology
- proactive_candidate: none
- memory_candidate: none
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
{raw_private}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (context / "attention_posture_state.md").write_text(
        """
- attention_target: owner_private
- attention_mode: wants_to_speak
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
    (context / "action_feedback_state.md").write_text(
        """
- status: active
- checked_at: 2026-05-27T14:40:21+08:00
- event_id: actfb-decision-chain
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
    learning = root / "memory/self/learning_closed_loop_state.md"
    learning.parent.mkdir(parents=True, exist_ok=True)
    learning.write_text(
        """
# Learning Closed Loop State

## Current Loop
- status: trial_active
- updated_at: 2026-05-27T14:42:00+08:00
- latest_event_id: learnloop-decision-chain
- latest_failure_kind: owner_reported_template_voice_failure
- active_trial_habit: direct replacement line, no feedback-processing phrase
- expected_next_behavior: change the next visible line without a repair report
- repair_count: 1
- success_count: 0
- success_streak: 0
- promotion_signal: false
- last_owner_reaction: repair_pressure
""".lstrip(),
        encoding="utf-8",
    )


def _seed_local_action_states(root: Path, raw_private: str) -> None:
    context = root / "memory/context"
    context.mkdir(parents=True, exist_ok=True)
    (context / "intention_ecology_state.md").write_text(
        f"""
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
{raw_private}
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


def test_decision_chain_latest_writes_visible_decision_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_DECISION_CHAIN_OWNER_TEXT_SHOULD_NOT_SURFACE_1301"
    raw_reply = "RAW_DECISION_CHAIN_REPLY_SHOULD_NOT_SURFACE_1302"
    _seed_visible_loop(tmp_path, raw_reply)
    _seed_common_states(tmp_path, raw_private)

    report = build_decision_chain_latest_report(tmp_path, now=NOW)
    output = render_decision_chain_latest_report(report)
    paths = write_decision_chain_latest(tmp_path, report)
    state = Path(paths["state_path"]).read_text(encoding="utf-8")
    trace = (tmp_path / "runtime/decision_chain_latest_trace.jsonl").read_text(encoding="utf-8")

    assert paths["report_path"] == str(decision_chain_latest_report_path(tmp_path))
    assert paths["state_path"] == str(decision_chain_latest_state_path(tmp_path))
    assert report["ok"] is True
    assert report["decision_chain"]["selected_candidate"] == "answer_current_turn"
    assert report["decision_chain"]["selected_total_score"] == "52"
    assert report["decision_chain"]["score_margin"] == "52"
    assert report["decision_chain"]["runner_up_not_selected_reason"] == "no_runner_up_to_compare"
    assert report["decision_chain"]["gate_pressure_summary"].startswith("selected_gate=current_turn_only")
    assert report["decision_chain"]["blocked_intents"] == "none"
    assert report["decision_chain"]["action_result"] == "visible_reply_sent_and_qq_ack_observed"
    assert report["decision_chain"]["action_evidence_lifecycle"] == "acked"
    assert report["decision_chain"]["perception_internal_consumed"] == "true"
    assert report["action_evidence_status"] == "verified"
    assert report["decision_chain"]["action_feedback_signal"] == "qq_visible_reply_ack"
    assert report["privacy"]["consciousness_claim"] is False
    assert "claim consciousness" in output
    for text in (output, state, trace):
        assert raw_private not in text
        assert raw_reply not in text


def test_decision_chain_latest_surfaces_local_action_evidence_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_DECISION_CHAIN_LOCAL_ACTION_SHOULD_NOT_SURFACE_3310"
    _seed_dispatch_only_loop(tmp_path)
    _seed_local_action_states(tmp_path, raw_private)

    report = build_decision_chain_latest_report(tmp_path, now=NOW)
    output = render_decision_chain_latest_report(report)

    assert report["ok"] is True
    assert report["decision_chain"]["selected_candidate"] == "do_bounded_task"
    assert report["decision_chain"]["action_result"] == (
        "local_action_result_observed:patch_executor/patch_task_prepared/prepared"
    )
    assert report["decision_chain"]["action_evidence_surface"] == "patch_executor"
    assert report["decision_chain"]["action_evidence_signal"] == "patch_task_prepared"
    assert report["decision_chain"]["action_evidence_result"] == "prepared"
    assert report["decision_chain"]["action_evidence_lifecycle"] == "prepared"
    assert report["decision_chain"]["next_behavior_bias"] == "patch_task_prepared_task_risk:-2"
    assert report["decision_chain"]["feedback_consumption_status"] == "consumed"
    assert "action_feedback_coverage:patch_task_prepared/prepared" in (
        report["decision_chain"]["feedback_consumed_sources"]
    )
    assert "action_feedback_coverage_bias:patch_task_prepared_task_risk:-2" in (
        report["decision_chain"]["feedback_consumed_biases"]
    )
    assert report["action_evidence_status"] == "verified"
    assert report["source_checks"]["feedback_consumption_auditable"]["ok"] is True
    assert raw_private not in output


def test_decision_chain_latest_surfaces_explained_silence_without_ack(tmp_path: Path) -> None:
    raw_private = "RAW_DECISION_CHAIN_SILENCE_SHOULD_NOT_SURFACE_7721"
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "decision-chain-silence",
                "stage": "queued",
                "recorded_at": "2026-05-27T14:40:00+08:00",
            },
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "decision-chain-silence",
                "stage": "dispatch_start",
                "recorded_at": "2026-05-27T14:40:05+08:00",
            },
        ],
    )
    context = tmp_path / "memory/context"
    context.mkdir(parents=True, exist_ok=True)
    (context / "intention_ecology_state.md").write_text(
        f"""
- selected_intent: hold_presence
- selected_gate: hold_or_silence
- action_level: silence
- autonomy_posture: bounded_restraint
- feedback_signal: none
- perception_gap_signal: owner_attention
- perception_gap_bias: owner_attention_current_turn_value:+6;require_short_term_anchor
- perception_route_hint: attention_posture_and_intention_ecology
- proactive_candidate: none
- memory_candidate: none
- restraint_reason: owner_needs_space
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
{raw_private}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    report = build_decision_chain_latest_report(tmp_path, now=NOW)
    output = render_decision_chain_latest_report(report)

    assert report["ok"] is True
    assert report["decision_chain"]["selected_candidate"] == "hold_presence"
    assert report["decision_chain"]["action_result"] == "bounded_non_action:hold_or_silence"
    assert report["decision_chain"]["restraint_reason"] == "owner_needs_space"
    assert report["decision_chain"]["runner_up_not_selected_reason"] == "lower_total_score:margin=16"
    assert report["decision_chain"]["held_intents"] == "hold_presence"
    assert report["decision_chain"]["action_evidence_lifecycle"] == "held"
    assert report["action_evidence_status"] == "bounded_non_action"
    assert report["source_checks"]["silence_or_hold_explained"]["ok"] is True
    assert raw_private not in output
