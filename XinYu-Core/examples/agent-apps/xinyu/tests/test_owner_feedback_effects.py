from __future__ import annotations

import json
from pathlib import Path

from xinyu_learning_closed_loop import record_learning_closed_loop_turn
from xinyu_owner_feedback_effects import build_owner_feedback_effect_report, write_owner_feedback_effect


OWNER_PRIVATE = {
    "message_type": "private_text",
    "session_id": "qq:private:owner",
    "metadata": {"is_owner_user": True},
}


def test_owner_feedback_effect_maps_template_feedback_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_OWNER_TEMPLATE_FEEDBACK_SHOULD_NOT_SURFACE_4138"
    record_learning_closed_loop_turn(
        tmp_path,
        OWNER_PRIVATE,
        user_text=f"{raw_private} 不要模板话",
        reply="知道了，我会改。",
        session_key="qq:private:owner",
        observed_at="2026-05-27T17:00:00+08:00",
    )

    report = build_owner_feedback_effect_report(tmp_path, generated_at="2026-05-27T17:00:01+08:00")
    write_owner_feedback_effect(tmp_path, report)

    state_text = (tmp_path / "memory/context/owner_feedback_effect_state.md").read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/owner_feedback_effect_trace.jsonl").read_text(encoding="utf-8")
    worklog_text = (tmp_path / "worklog/xinyu-owner-feedback-effect-latest.md").read_text(encoding="utf-8")

    assert report["status"] == "active"
    assert report["latest_feedback_kind"] == "owner_reported_template_voice_failure"
    assert report["expression_strategy_bias"] == "avoid_template_or_feedback_processing_phrase"
    assert report["intention_bias"] == "repair_relation_visible_risk:-6"
    assert report["future_effect"] == "prefer_concrete_replacement_line_over_feedback_processing"
    assert report["privacy"]["raw_owner_text_retained"] is False
    assert raw_private not in state_text
    assert raw_private not in trace_text
    assert raw_private not in worklog_text
    assert "stable_personality_write: blocked" in state_text


def test_owner_feedback_effect_caps_overloaded_template_pressure_for_realtime(tmp_path: Path) -> None:
    raw_private = "RAW_OVERLOADED_TEMPLATE_PRESSURE_SHOULD_NOT_SURFACE_4139"
    state_path = tmp_path / "memory/self/learning_closed_loop_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        f"""# Learning Closed Loop State

## Current Loop
- status: trial_active
- updated_at: 2026-05-27T17:00:00+08:00
- latest_event_id: learnloop-overloaded-style
- latest_failure_kind: owner_reported_template_voice_failure
- active_trial_key: owner_reported_template_voice_failure
- active_trial_habit: direct replacement line, no feedback-processing phrase
- expected_next_behavior: change the next visible line without a repair report
- repair_count: 94
- success_count: 3
- success_streak: 0
- trial_success_count: 3
- trial_success_streak: 0
- promotion_signal: false
- last_owner_reaction: repair_pressure

## Success Evidence
- latest_success_trial_key: none
- success_evidence_status: none
{raw_private}
""",
        encoding="utf-8",
    )

    report = build_owner_feedback_effect_report(tmp_path, generated_at="2026-05-27T17:00:01+08:00")
    write_owner_feedback_effect(tmp_path, report)

    state_text = (tmp_path / "memory/context/owner_feedback_effect_state.md").read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/owner_feedback_effect_trace.jsonl").read_text(encoding="utf-8")

    assert report["status"] == "active"
    assert report["latest_feedback_kind"] == "owner_reported_template_voice_failure"
    assert report["expression_strategy_bias"] == "style_repair_pressure_capped_keep_current_turn_anchor"
    assert report["intention_bias"] == "repair_relation_visible_risk:-2"
    assert report["future_effect"] == "style_repair_direct_only_ordinary_chat_keeps_current_anchor"
    assert report["realtime_pressure_status"] == "capped_direct_failure_only"
    assert "repair_pressure_overloaded:94" in report["realtime_pressure_reason"]
    assert raw_private not in state_text
    assert raw_private not in trace_text
    assert "realtime_pressure_status: capped_direct_failure_only" in state_text


def test_owner_feedback_effect_maps_memory_mechanics_leak_to_visible_reply_bias(tmp_path: Path) -> None:
    raw_private = "RAW_MEMORY_MECHANICS_LEAK_SHOULD_NOT_SURFACE_7321"
    state_path = tmp_path / "memory/self/learning_closed_loop_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        f"""# Learning Closed Loop State

## Current Loop
- status: trial_active
- updated_at: 2026-05-31T17:00:00+08:00
- latest_event_id: learnloop-memory-mechanics
- latest_failure_kind: memory_mechanics_leak
- active_trial_key: memory_mechanics_leak
- active_trial_habit: hold the conversation first, no file or state-card reading posture
- expected_next_behavior: answer without exposing memory machinery
- repair_count: 3
- success_count: 1
- success_streak: 0
- trial_success_count: 1
- trial_success_streak: 0
- promotion_signal: false
- last_owner_reaction: repair_pressure

## Success Evidence
- latest_success_trial_key: none
- success_evidence_status: none
{raw_private}
""",
        encoding="utf-8",
    )

    report = build_owner_feedback_effect_report(tmp_path, generated_at="2026-05-31T17:00:01+08:00")
    write_owner_feedback_effect(tmp_path, report)

    state_text = (tmp_path / "memory/context/owner_feedback_effect_state.md").read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/owner_feedback_effect_trace.jsonl").read_text(encoding="utf-8")

    # The owner correction must now define a concrete future effect (previously future_effect=none).
    assert report["ok"] is True
    assert report["status"] == "active"
    assert report["latest_feedback_kind"] == "memory_mechanics_leak"
    assert report["expression_strategy_bias"] == "avoid_memory_mechanics_in_visible_reply"
    # Reuses the existing visible-reply mechanism-leak risk handler in xinyu_intention_ecology.
    assert report["intention_bias"] == "visible_mechanism_leak_risk:+12"
    assert (
        report["future_effect"]
        == "avoid_memory_mechanics_in_visible_reply_unless_owner_requests_diagnostics"
    )
    assert report["privacy"]["stable_personality_write"] == "blocked"
    assert raw_private not in state_text
    assert raw_private not in trace_text


def test_owner_feedback_effect_maps_explicit_success_to_supported_trial(tmp_path: Path) -> None:
    record_learning_closed_loop_turn(
        tmp_path,
        OWNER_PRIVATE,
        user_text="不要模板话",
        reply="知道了，我会改。",
        session_key="qq:private:owner",
        observed_at="2026-05-27T17:01:00+08:00",
    )
    record_learning_closed_loop_turn(
        tmp_path,
        OWNER_PRIVATE,
        user_text="这句自然多了",
        reply="嗯。",
        session_key="qq:private:owner",
        observed_at="2026-05-27T17:02:00+08:00",
    )

    report = build_owner_feedback_effect_report(tmp_path, generated_at="2026-05-27T17:02:01+08:00")

    assert report["status"] == "supported"
    assert report["latest_feedback_kind"] == "explicit_success"
    assert report["owner_reaction"] == "explicit_success"
    assert report["expression_strategy_bias"] == "keep_current_style_trial"
    assert report["intention_bias"] == "current_trial_risk:-3"
    assert report["success_count"] == 1
    assert report["success_streak"] == 1
    assert report["trial_success_count"] == 1
    assert report["trial_success_streak"] == 1
    assert report["latest_success_trial_key"] == "owner_reported_template_voice_failure"
    assert report["success_evidence_status"] == "same_trial_explicit_owner_success"
    assert report["privacy"]["stable_personality_write"] == "blocked"


def test_owner_feedback_effect_can_use_post_reply_observation_signal(tmp_path: Path) -> None:
    trace_path = tmp_path / "runtime/post_reply_self_observation_trace.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        json.dumps(
            {
                "observed_at": "2026-05-27T17:03:00+08:00",
                "owner_private": True,
                "scores": {
                    "alive_voice": "low",
                    "mechanical_risk": "low",
                    "template_risk": "high",
                    "over_explained_risk": "medium",
                },
                "notes": ["post_reply_observation_recorded", "post_reply_template_voice_risk"],
                "raw_text_saved": False,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_owner_feedback_effect_report(tmp_path, generated_at="2026-05-27T17:03:01+08:00")

    assert report["status"] == "active"
    assert report["latest_feedback_kind"] == "post_reply_template_voice_risk"
    assert report["owner_reaction"] == "post_reply_self_observation"
    assert report["expression_strategy_bias"] == "avoid_template_voice_after_reply"
    assert report["intention_bias"] == "repair_relation_visible_risk:-4"


def test_owner_feedback_effect_maps_low_information_ack_signal(tmp_path: Path) -> None:
    trace_path = tmp_path / "runtime/post_reply_self_observation_trace.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        json.dumps(
            {
                "observed_at": "2026-05-27T17:03:30+08:00",
                "owner_private": True,
                "scores": {
                    "alive_voice": "low",
                    "mechanical_risk": "low",
                    "template_risk": "low",
                    "over_explained_risk": "low",
                    "low_information_ack_risk": "high",
                },
                "notes": ["post_reply_observation_recorded", "post_reply_low_information_ack_risk"],
                "raw_text_saved": False,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_owner_feedback_effect_report(tmp_path, generated_at="2026-05-27T17:03:31+08:00")

    assert report["status"] == "active"
    assert report["latest_feedback_kind"] == "post_reply_low_information_ack_risk"
    assert report["expression_strategy_bias"] == "replace_bare_ack_with_one_specific_current_anchor"
    assert report["intention_bias"] == "low_information_ack_risk:+8"


def test_owner_feedback_effect_maps_desktop_dismissed_response_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_DESKTOP_DISMISS_SHOULD_NOT_SURFACE_5541"
    state_path = tmp_path / "memory/context/proactive_request_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        f"""# Proactive Request State

- status: dismissed
- checked_at: 2026-05-27T17:04:00+08:00
- request_id: proactive-dismiss-test
- request_answer_state: dismissed
- last_ack_status: dismissed
- requested_action: ask_owner
{raw_private}
""",
        encoding="utf-8",
    )

    report = build_owner_feedback_effect_report(tmp_path, generated_at="2026-05-27T17:04:01+08:00")
    write_owner_feedback_effect(tmp_path, report)

    state_text = (tmp_path / "memory/context/owner_feedback_effect_state.md").read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/owner_feedback_effect_trace.jsonl").read_text(encoding="utf-8")
    rendered = (tmp_path / "worklog/xinyu-owner-feedback-effect-latest.md").read_text(encoding="utf-8")

    assert report["status"] == "response_active"
    assert report["owner_response_signal"] == "desktop_dismissed"
    assert report["owner_response_strategy_bias"] == "lower_same_request_priority"
    assert report["owner_response_intention_bias"] == "proactive_future_block:+10"
    assert report["owner_response_future_effect"] == "lower_same_request_priority_until_new_evidence"
    assert raw_private not in state_text
    assert raw_private not in trace_text
    assert raw_private not in rendered


def test_owner_feedback_effect_maps_no_response_timeout_as_ignore_feedback(tmp_path: Path) -> None:
    state_path = tmp_path / "memory/context/proactive_request_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Proactive Request State

- status: sent
- created_at: 2026-05-27T13:00:00+08:00
- request_id: proactive-ignore-test
- request_answer_state: sent_waiting_owner_reply
- last_ack_status: sent
- requested_action: ask_owner
""",
        encoding="utf-8",
    )

    report = build_owner_feedback_effect_report(tmp_path, generated_at="2026-05-27T17:00:00+08:00")

    assert report["status"] == "response_active"
    assert report["owner_response_signal"] == "owner_no_response_timeout"
    assert report["owner_response_source"] == "proactive_request_timeout"
    assert report["owner_response_strategy_bias"] == "enter_observation_and_reduce_repeat_request"
    assert report["owner_response_intention_bias"] == "proactive_repeat_risk:+12"
