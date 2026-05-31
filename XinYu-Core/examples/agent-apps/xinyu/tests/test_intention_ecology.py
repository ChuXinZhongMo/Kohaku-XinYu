import json
from pathlib import Path

from xinyu_intention_ecology import build_intention_ecology_prompt_block
from xinyu_intention_ecology import evaluate_intention_ecology
from xinyu_intention_ecology import read_intention_ecology_state
from xinyu_learning_closed_loop import record_learning_closed_loop_turn
from xinyu_relation_posture import evaluate_relation_posture
from xinyu_turn_classifier import classify_visible_turn


def _owner_payload() -> dict:
    return {"metadata": {"is_owner_user": True}, "message_type": "private_text"}


def _external_payload() -> dict:
    return {"metadata": {"is_owner_user": False}, "message_type": "group_text"}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _write_action_feedback_state(
    root: Path,
    *,
    feedback_signal: str,
    action_result: str,
    future_effect: str,
    memory_effect: str = "none",
    extra_lines: tuple[str, ...] = (),
) -> None:
    context = root / "memory/context"
    context.mkdir(parents=True, exist_ok=True)
    extra = "\n".join(extra_lines)
    if extra:
        extra = "\n" + extra
    (context / "action_feedback_state.md").write_text(
        f"""
- status: active
- checked_at: 2026-05-27T15:00:00+08:00
- feedback_signal: {feedback_signal}
- action_result: {action_result}
- future_effect: {future_effect}
- memory_effect: {memory_effect}
- raw_private_body_retained: false
- visible_reply_text_retained: false
- stable_memory_write: blocked{extra}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_intention_ecology_repairs_relationship_pressure_with_gated_memory_candidate(tmp_path: Path) -> None:
    visible = classify_visible_turn(tmp_path, payload=_owner_payload(), user_text="你又变回接待腔了，还是没变")
    relation = evaluate_relation_posture(
        tmp_path,
        _owner_payload(),
        user_text="你又变回接待腔了，还是没变",
        visible_turn=visible,
    )

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="你又变回接待腔了，还是没变",
        dialogue_tail=[{"role": "assistant", "content": "我会改。"}],
        relation_posture=relation,
        visible_turn=visible,
        checked_at="2026-05-24T05:00:00+08:00",
        write_state=True,
    )

    state = read_intention_ecology_state(tmp_path)
    prompt_block = build_intention_ecology_prompt_block(tmp_path, ecology)
    assert ecology.selected_intent == "repair_relation"
    assert ecology.selected_gate == "current_turn_only"
    assert ecology.feedback_signal == "negative"
    assert ecology.candidate_competition_status == "observed"
    assert ecology.selected_total_score == ecology.candidates[0].total_score
    assert ecology.runner_up_intent == ecology.candidates[1].intent_type
    assert ecology.score_margin == ecology.candidates[0].total_score - ecology.candidates[1].total_score
    assert ecology.runner_up_not_selected_reason.startswith("lower_total_score:")
    assert "selected_gate=current_turn_only" in ecology.gate_pressure_summary
    assert ecology.memory_candidate == "review_gated:repair_relation"
    assert ecology.proactive_candidate == "none"
    assert state["selected_intent"] == "repair_relation"
    assert state["candidate_competition_status"] == "observed"
    assert state["runner_up_intent"] == ecology.runner_up_intent
    assert state["score_margin"] == str(ecology.score_margin)
    assert state["runner_up_not_selected_reason"].startswith("lower_total_score:")
    assert state["gate_pressure_summary"].startswith("selected_gate=current_turn_only")
    assert state["stable_memory_write"] == "gated"
    assert "intention ecology sidecar:" in prompt_block
    assert "visibility_rule: hidden" in prompt_block
    assert "do not mention ecology, candidates, gates, scores" in prompt_block
    assert "human_style_rule:" in prompt_block
    assert "runner_up_not_selected_reason:" in prompt_block
    assert "gate_pressure_summary:" in prompt_block
    assert "do not say '知道了' as a standalone opener" in prompt_block


def test_intention_ecology_treats_not_like_real_person_as_repair_pressure(tmp_path: Path) -> None:
    text = "知道了。这句是真的，没在接话。 但我觉得这句 不像真人啊"
    visible = classify_visible_turn(tmp_path, payload=_owner_payload(), user_text=text)
    relation = evaluate_relation_posture(tmp_path, _owner_payload(), user_text=text, visible_turn=visible)

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text=text,
        relation_posture=relation,
        visible_turn=visible,
    )
    prompt_block = build_intention_ecology_prompt_block(tmp_path, ecology)

    assert ecology.selected_intent == "repair_relation"
    assert ecology.feedback_signal == "negative"
    assert "human_style_rule:" in prompt_block
    assert "anti_service_rule:" in prompt_block



def test_intention_ecology_rest_chooses_restraint_without_probe(tmp_path: Path) -> None:
    visible = classify_visible_turn(tmp_path, payload=_owner_payload(), user_text="我好累，先别问了")
    relation = evaluate_relation_posture(tmp_path, _owner_payload(), user_text="我好累，先别问了", visible_turn=visible)

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="我好累，先别问了",
        relation_posture=relation,
        visible_turn=visible,
    )

    assert ecology.selected_intent == "hold_presence"
    assert ecology.selected_gate == "hold_or_silence"
    assert ecology.autonomy_posture == "bounded_restraint"
    assert ecology.restraint_reason == "owner_needs_space"
    assert ecology.proactive_candidate == "none"


def test_intention_ecology_emotional_companionship_records_gated_followup_candidate(tmp_path: Path) -> None:
    visible = classify_visible_turn(tmp_path, payload=_owner_payload(), user_text="有点难受，陪我一下")
    relation = evaluate_relation_posture(tmp_path, _owner_payload(), user_text="有点难受，陪我一下", visible_turn=visible)

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="有点难受，陪我一下",
        relation_posture=relation,
        visible_turn=visible,
    )

    assert ecology.selected_intent == "comfort_quietly"
    assert ecology.selected_gate == "current_turn_only"
    assert ecology.proactive_candidate == "review_gated:comfort_quietly"
    assert ecology.autonomy_posture == "current_reply_plus_gated_future_candidate"


def test_intention_ecology_external_sender_blocks_future_action(tmp_path: Path) -> None:
    visible = classify_visible_turn(tmp_path, payload=_external_payload(), user_text="有点难受，陪我一下")
    relation = evaluate_relation_posture(tmp_path, _external_payload(), user_text="有点难受，陪我一下", visible_turn=visible)

    ecology = evaluate_intention_ecology(
        tmp_path,
        _external_payload(),
        user_text="有点难受，陪我一下",
        relation_posture=relation,
        visible_turn=visible,
    )

    assert ecology.proactive_candidate == "none"
    assert all(candidate.future_candidate == "none" for candidate in ecology.candidates)
    assert any("future_action_blocked_by_relation_or_sender" in candidate.reason for candidate in ecology.candidates)


def test_intention_ecology_writes_trace_without_raw_private_body(tmp_path: Path) -> None:
    visible = classify_visible_turn(tmp_path, payload=_owner_payload(), user_text="我有点焦虑，怎么办")
    relation = evaluate_relation_posture(tmp_path, _owner_payload(), user_text="我有点焦虑，怎么办", visible_turn=visible)

    evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="我有点焦虑，怎么办",
        relation_posture=relation,
        visible_turn=visible,
        checked_at="2026-05-24T05:01:00+08:00",
        write_state=True,
    )

    state_text = (tmp_path / "memory/context/intention_ecology_state.md").read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/intention_ecology_trace.jsonl").read_text(encoding="utf-8")
    assert "raw_private_body_retained: false" in state_text
    assert "我有点焦虑" not in state_text
    assert "我有点焦虑" not in trace_text
    assert "give_one_small_next_step" in trace_text


def test_intention_ecology_action_ack_feedback_lowers_visible_reply_risk_and_records_bias(tmp_path: Path) -> None:
    relation = {"scene": "technical_or_system_design", "initiative_allowed": "unchanged", "risk_level": "low"}
    baseline = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="please continue the bounded task",
        relation_posture=relation,
    )
    _write_action_feedback_state(
        tmp_path,
        feedback_signal="qq_visible_reply_ack",
        action_result="delivered",
        future_effect="confirm_visible_reply_transport_for_next_turn",
        memory_effect="sent_reply_index_updated",
    )

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="please continue the bounded task",
        relation_posture=relation,
        checked_at="2026-05-27T15:01:00+08:00",
        write_state=True,
    )

    baseline_task = next(candidate for candidate in baseline.candidates if candidate.intent_type == "do_bounded_task")
    ack_task = next(candidate for candidate in ecology.candidates if candidate.intent_type == "do_bounded_task")
    state = read_intention_ecology_state(tmp_path)
    assert ecology.action_feedback_signal == "qq_visible_reply_ack"
    assert ecology.action_feedback_bias == "route_confirmed_visible_reply_risk:-4"
    assert ack_task.risk_score == baseline_task.risk_score - 4
    assert "action_feedback_route_confirmed" in ack_task.reason
    assert state["action_feedback_signal"] == "qq_visible_reply_ack"
    assert state["action_feedback_bias"] == "route_confirmed_visible_reply_risk:-4"


def test_intention_ecology_stale_drop_blocks_proactive_future_candidate(tmp_path: Path) -> None:
    relation = {"scene": "emotional_signal", "initiative_allowed": "unchanged", "risk_level": "low"}
    _write_action_feedback_state(
        tmp_path,
        feedback_signal="qq_stale_reply_drop",
        action_result="unsent_retracted",
        future_effect="prefer_latest_owner_input_and_suppress_stale_reply_memory",
        memory_effect="unsent_reply_retracted",
    )

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="quiet companion turn",
        relation_posture=relation,
        checked_at="2026-05-27T15:02:00+08:00",
        write_state=True,
    )

    comfort = next(candidate for candidate in ecology.candidates if candidate.intent_type == "comfort_quietly")
    state = read_intention_ecology_state(tmp_path)
    assert ecology.action_feedback_signal == "qq_stale_reply_drop"
    assert ecology.action_feedback_bias == "stale_reply_future_candidate_blocked_visible_risk:+8"
    assert ecology.proactive_candidate == "none"
    assert comfort.future_candidate == "none"
    assert "future_candidate_blocked_until_fresh_turn" in comfort.reason
    assert state["action_feedback_bias"] == "stale_reply_future_candidate_blocked_visible_risk:+8"


def test_intention_ecology_action_feedback_does_not_copy_raw_private_or_visible_text(tmp_path: Path) -> None:
    raw_private = "RAW_PRIVATE_BODY_SHOULD_NOT_COPY_7923"
    visible_reply = "VISIBLE_REPLY_BODY_SHOULD_NOT_COPY_4529"
    relation = {"scene": "technical_or_system_design", "initiative_allowed": "unchanged", "risk_level": "low"}
    _write_action_feedback_state(
        tmp_path,
        feedback_signal="qq_visible_reply_ack",
        action_result="delivered",
        future_effect="confirm_visible_reply_transport_for_next_turn",
        memory_effect="sent_reply_index_updated",
        extra_lines=(f"- raw_private_body: {raw_private}", f"- visible_reply_text: {visible_reply}"),
    )

    evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text=raw_private,
        relation_posture=relation,
        checked_at="2026-05-27T15:03:00+08:00",
        write_state=True,
    )

    state_text = (tmp_path / "memory/context/intention_ecology_state.md").read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/intention_ecology_trace.jsonl").read_text(encoding="utf-8")
    assert raw_private not in state_text
    assert raw_private not in trace_text
    assert visible_reply not in state_text
    assert visible_reply not in trace_text
    assert "action_feedback_bias" in state_text


def test_intention_ecology_local_tool_feedback_lowers_bounded_task_risk(tmp_path: Path) -> None:
    relation = {"scene": "technical_or_system_design", "initiative_allowed": "unchanged", "risk_level": "low"}
    baseline = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="please continue the bounded task",
        relation_posture=relation,
    )
    _write_jsonl(
        tmp_path / "runtime/self_action_gateway/trace.jsonl",
        [
            {
                "event_kind": "self_action_executed",
                "checked_at": "2026-05-27T16:00:00+08:00",
                "action_id": "selfact-local-ok",
                "action_kind": "local_py_compile_probe",
                "status": "executed",
                "result": "success",
                "error_code": "",
            }
        ],
    )

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="please continue the bounded task",
        relation_posture=relation,
        checked_at="2026-05-27T16:01:00+08:00",
        write_state=True,
    )

    baseline_task = next(candidate for candidate in baseline.candidates if candidate.intent_type == "do_bounded_task")
    tool_task = next(candidate for candidate in ecology.candidates if candidate.intent_type == "do_bounded_task")
    state = read_intention_ecology_state(tmp_path)
    assert ecology.action_feedback_coverage_signal == "local_tool_probe_succeeded"
    assert ecology.action_feedback_coverage_lifecycle == "succeeded"
    assert "local_tool_probe_succeeded_task_risk:-3" in ecology.action_feedback_coverage_bias
    assert ecology.feedback_consumption_status == "consumed"
    assert "action_feedback_coverage:local_tool_probe_succeeded/succeeded" in ecology.feedback_consumed_sources
    assert "action_feedback_coverage_bias:local_tool_probe_succeeded_task_risk:-3" in ecology.feedback_consumed_biases
    assert "action_feedback_coverage_future:keep_low_risk_probe_available_for_bounded_checks" in (
        ecology.feedback_consumed_future_effect
    )
    assert tool_task.risk_score == baseline_task.risk_score - 3
    assert "coverage_local_tool_probe_succeeded" in tool_task.reason
    assert state["action_feedback_coverage_signal"] == "local_tool_probe_succeeded"
    assert state["action_feedback_coverage_lifecycle"] == "succeeded"
    assert "local_tool_probe_succeeded_task_risk:-3" in state["action_feedback_coverage_bias"]
    assert state["feedback_consumption_status"] == "consumed"
    assert "action_feedback_coverage:local_tool_probe_succeeded/succeeded" in state["feedback_consumed_sources"]


def test_intention_ecology_running_action_lifecycle_raises_task_claim_risk(tmp_path: Path) -> None:
    relation = {"scene": "technical_or_system_design", "initiative_allowed": "unchanged", "risk_level": "low"}
    baseline = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="please continue the bounded task",
        relation_posture=relation,
    )
    _write(
        tmp_path / "memory/context/self_action_patch_executor_state.md",
        """
        - checked_at: 2026-05-27T16:01:00+08:00
        - status: running
        - execution_level: apply
        - queue_id: queue-running
        - task_id: patch-running
        - codex_status: not_requested
        """,
    )

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="please continue the bounded task",
        relation_posture=relation,
        checked_at="2026-05-27T16:01:30+08:00",
        write_state=True,
    )

    baseline_task = next(candidate for candidate in baseline.candidates if candidate.intent_type == "do_bounded_task")
    running_task = next(candidate for candidate in ecology.candidates if candidate.intent_type == "do_bounded_task")
    state = read_intention_ecology_state(tmp_path)
    assert ecology.action_feedback_coverage_signal == "patch_executor_state_seen"
    assert ecology.action_feedback_coverage_lifecycle == "running"
    assert ecology.action_feedback_coverage_bias == "action_lifecycle_running_task_claim_risk:+8"
    assert running_task.risk_score == baseline_task.risk_score + 8
    assert "coverage_lifecycle_running_wait_for_terminal_result" in running_task.reason
    assert "wait for the current action result before claiming completion" in running_task.visible_bias
    assert state["action_feedback_coverage_lifecycle"] == "running"
    assert state["action_feedback_coverage_bias"] == "action_lifecycle_running_task_claim_risk:+8"


def test_intention_ecology_code_restart_feedback_raises_task_claim_risk(tmp_path: Path) -> None:
    relation = {"scene": "technical_or_system_design", "initiative_allowed": "unchanged", "risk_level": "low"}
    baseline = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="please continue the bounded task",
        relation_posture=relation,
    )
    _write(
        tmp_path / "memory/context/code_change_awareness_state.md",
        """
        - updated_at: 2026-05-27T16:02:00+08:00
        - status: changed
        - source_changed: true
        - current_project_digest: abc123
        - bridge_restart_required: true
        - runtime_restart_required: false
        - gateway_restart_may_be_needed: false
        """,
    )

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="please continue the bounded task",
        relation_posture=relation,
        checked_at="2026-05-27T16:03:00+08:00",
        write_state=True,
    )

    baseline_task = next(candidate for candidate in baseline.candidates if candidate.intent_type == "do_bounded_task")
    restart_task = next(candidate for candidate in ecology.candidates if candidate.intent_type == "do_bounded_task")
    assert ecology.action_feedback_coverage_signal == "code_probe_restart_required"
    assert "code_probe_restart_required_task_claim_risk:+20" in ecology.action_feedback_coverage_bias
    assert ecology.perception_gap_signal == "maintenance_gap"
    assert "maintenance_gap_task_claim_risk:+6" in ecology.perception_gap_bias
    assert restart_task.risk_score == baseline_task.risk_score + 26
    assert "coverage_restart_required_before_source_claim" in restart_task.reason
    assert "verify restart/load state before claiming code took effect" in restart_task.visible_bias
    assert "verify runtime/source state before claiming task effect" in restart_task.visible_bias


def test_intention_ecology_coverage_feedback_does_not_copy_runtime_previews(tmp_path: Path) -> None:
    raw_private = "RAW_RUNTIME_PREVIEW_SHOULD_NOT_COPY_3912"
    raw_reply = "RAW_RUNTIME_REPLY_SHOULD_NOT_COPY_3913"
    relation = {"scene": "technical_or_system_design", "initiative_allowed": "unchanged", "risk_level": "low"}
    _write(
        tmp_path / "memory/context/runtime_self_presence.md",
        f"""
        - bridge_process: running
        - current_turn_state: idle
        - last_turn_id: turn-preview
        - last_turn_at: 2026-05-27T16:04:00+08:00
        - last_turn_status: ok
        - last_user_preview: {raw_private}
        - last_reply_preview: {raw_reply}
        """,
    )

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text=raw_private,
        relation_posture=relation,
        checked_at="2026-05-27T16:05:00+08:00",
        write_state=True,
    )

    state_text = (tmp_path / "memory/context/intention_ecology_state.md").read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/intention_ecology_trace.jsonl").read_text(encoding="utf-8")
    assert ecology.action_feedback_coverage_signal == "runtime_probe_ok"
    assert raw_private not in state_text
    assert raw_private not in trace_text
    assert raw_reply not in state_text
    assert raw_reply not in trace_text
    assert "action_feedback_coverage_bias" in state_text


def test_intention_ecology_owner_feedback_effect_lowers_style_repair_risk(tmp_path: Path) -> None:
    text = "你又变回模板话了"
    visible = classify_visible_turn(tmp_path, payload=_owner_payload(), user_text=text)
    relation = evaluate_relation_posture(tmp_path, _owner_payload(), user_text=text, visible_turn=visible)
    baseline = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text=text,
        relation_posture=relation,
        visible_turn=visible,
        checked_at="2026-05-27T17:04:00+08:00",
    )
    raw_private = "RAW_OWNER_EFFECT_SHOULD_NOT_SURFACE_9362"
    record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text=f"{raw_private} 不要模板话",
        reply="知道了，我会改。",
        session_key="qq:private:owner",
        observed_at="2026-05-27T17:04:01+08:00",
    )

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text=text,
        relation_posture=relation,
        visible_turn=visible,
        checked_at="2026-05-27T17:04:02+08:00",
        write_state=True,
    )

    baseline_repair = next(candidate for candidate in baseline.candidates if candidate.intent_type == "repair_relation")
    effect_repair = next(candidate for candidate in ecology.candidates if candidate.intent_type == "repair_relation")
    state = read_intention_ecology_state(tmp_path)
    owner_effect_state = (tmp_path / "memory/context/owner_feedback_effect_state.md").read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/intention_ecology_trace.jsonl").read_text(encoding="utf-8")

    assert ecology.owner_feedback_effect_signal == "owner_reported_template_voice_failure"
    assert ecology.owner_feedback_effect_bias == "repair_relation_visible_risk:-6"
    assert ecology.owner_feedback_expression_bias == "avoid_template_or_feedback_processing_phrase"
    assert effect_repair.risk_score == baseline_repair.risk_score - 6
    assert "owner_feedback_style_repair_pressure" in effect_repair.reason
    assert "owner_feedback:avoid_template_or_feedback_processing_phrase" in effect_repair.visible_bias
    assert state["owner_feedback_effect_signal"] == "owner_reported_template_voice_failure"
    assert state["owner_feedback_effect_bias"] == "repair_relation_visible_risk:-6"
    assert raw_private not in owner_effect_state
    assert raw_private not in trace_text


def test_intention_ecology_memory_mechanics_leak_raises_visible_reply_risk(tmp_path: Path) -> None:
    # Baseline first, with no owner correction on record.
    baseline = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="接下来继续做什么",
        relation_posture={"scene": "ordinary_owner_chat", "initiative_allowed": "unchanged", "risk_level": "low"},
        checked_at="2026-05-31T17:05:00+08:00",
    )
    baseline_answer = next(c for c in baseline.candidates if c.intent_type == "answer_current_turn")

    _write(
        tmp_path / "memory/self/learning_closed_loop_state.md",
        """
        - status: trial_active
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
        - latest_success_trial_key: none
        - success_evidence_status: none
        - promotion_signal: false
        - last_owner_reaction: repair_pressure
        """,
    )

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="接下来继续做什么",
        relation_posture={"scene": "ordinary_owner_chat", "initiative_allowed": "unchanged", "risk_level": "low"},
        checked_at="2026-05-31T17:05:01+08:00",
        write_state=True,
    )
    effect_answer = next(c for c in ecology.candidates if c.intent_type == "answer_current_turn")

    assert ecology.owner_feedback_effect_signal == "memory_mechanics_leak"
    assert ecology.owner_feedback_effect_bias == "visible_mechanism_leak_risk:+12"
    assert ecology.owner_feedback_expression_bias == "avoid_memory_mechanics_in_visible_reply"
    assert effect_answer.risk_score == baseline_answer.risk_score + 4
    assert "owner_feedback_visible_mechanism_leak_recently" in effect_answer.reason
    assert "owner_feedback:avoid_memory_mechanics_in_visible_reply" in effect_answer.visible_bias


def test_intention_ecology_caps_overloaded_style_pressure_on_ordinary_turn(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/self/learning_closed_loop_state.md",
        """
        - status: trial_active
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
        - latest_success_trial_key: none
        - success_evidence_status: none
        - promotion_signal: false
        - last_owner_reaction: repair_pressure
        """,
    )

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="接下来继续做什么",
        relation_posture={"scene": "ordinary_owner_chat", "initiative_allowed": "unchanged", "risk_level": "low"},
        checked_at="2026-05-27T17:05:00+08:00",
        write_state=True,
    )

    state = read_intention_ecology_state(tmp_path)
    owner_effect_state = (tmp_path / "memory/context/owner_feedback_effect_state.md").read_text(encoding="utf-8")

    assert ecology.selected_intent == "answer_current_turn"
    assert ecology.owner_feedback_effect_signal == "none"
    assert ecology.owner_feedback_effect_bias == "none"
    assert ecology.owner_feedback_expression_bias == "none"
    assert "owner_feedback:style_repair_pressure_capped_keep_current_turn_anchor" not in ecology.candidates[0].visible_bias
    assert "owner_feedback_effect_cooldown:direct_failure_only" in ecology.notes
    assert state["owner_feedback_effect_bias"] == "none"
    assert "realtime_pressure_status: capped_direct_failure_only" in owner_effect_state


def test_intention_ecology_uses_overloaded_style_pressure_on_direct_failure_turn(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/self/learning_closed_loop_state.md",
        """
        - status: trial_active
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
        - latest_success_trial_key: none
        - success_evidence_status: none
        - promotion_signal: false
        - last_owner_reaction: repair_pressure
        """,
    )

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="这句又是模板味",
        relation_posture={"scene": "ordinary_owner_chat", "initiative_allowed": "unchanged", "risk_level": "low"},
        checked_at="2026-05-27T17:05:00+08:00",
    )

    assert ecology.selected_intent == "repair_relation"
    assert ecology.owner_feedback_effect_signal == "owner_reported_template_voice_failure"
    assert ecology.owner_feedback_effect_bias == "repair_relation_visible_risk:-2"
    assert ecology.owner_feedback_expression_bias == "style_repair_pressure_capped_keep_current_turn_anchor"
    assert "owner_feedback:style_repair_pressure_capped_keep_current_turn_anchor" in ecology.candidates[0].visible_bias


def test_intention_ecology_owner_response_approval_lowers_proactive_risk(tmp_path: Path) -> None:
    relation = {"scene": "emotional_signal", "initiative_allowed": "unchanged", "risk_level": "low"}
    baseline = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="有点难受，陪我一下",
        relation_posture=relation,
        checked_at="2026-05-27T17:06:00+08:00",
    )
    _write(
        tmp_path / "memory/context/proactive_request_state.md",
        """
        - status: approved
        - checked_at: 2026-05-27T17:06:01+08:00
        - request_id: proactive-approval-test
        - request_answer_state: approved_qq
        - last_ack_status: approved_qq
        - requested_action: ask_owner
        """,
    )

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="有点难受，陪我一下",
        relation_posture=relation,
        checked_at="2026-05-27T17:06:02+08:00",
        write_state=True,
    )

    baseline_comfort = next(candidate for candidate in baseline.candidates if candidate.intent_type == "comfort_quietly")
    approved_comfort = next(candidate for candidate in ecology.candidates if candidate.intent_type == "comfort_quietly")
    state = read_intention_ecology_state(tmp_path)

    assert ecology.owner_response_feedback_signal == "desktop_approved_qq"
    assert ecology.owner_response_feedback_bias == "one_time_qq_permission:+8"
    assert ecology.owner_response_strategy_bias == "allow_one_bounded_qq_enqueue_if_gates_pass"
    assert approved_comfort.risk_score == baseline_comfort.risk_score - 8
    assert approved_comfort.value_score == baseline_comfort.value_score + 8
    assert "owner_response_one_time_qq_permission" in approved_comfort.reason
    assert state["owner_response_feedback_signal"] == "desktop_approved_qq"
    assert state["owner_response_feedback_bias"] == "one_time_qq_permission:+8"


def test_intention_ecology_perception_repair_gap_blocks_proactive_candidate(tmp_path: Path) -> None:
    raw_private = "RAW_PERCEPTION_GAP_SHOULD_NOT_COPY_8801"
    relation = {"scene": "emotional_signal", "initiative_allowed": "unchanged", "risk_level": "low"}
    perception_report = {
        "status": "pass",
        "metrics": {
            "latest_gap_type": "repair_gap",
            "latest_future_effect": "prefer_latest_input_and_retraction_before_any_visible_reply",
            "latest_event_ref": "sha256:repair-gap",
            "max_attention_weight": 95,
            "next_route_hint": "gate_repair_before_visible_send",
        },
        "judgments": [
            {
                "event_id": "percevt-repair",
                "gap_type": "repair_gap",
                "suggested_route": "gate_repair_before_visible_send",
                "future_effect": "prefer_latest_input_and_retraction_before_any_visible_reply",
                "attention_weight": 95,
                "evidence_ref": "sha256:repair-gap",
                "raw_private_body": raw_private,
            }
        ],
    }

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="quiet companion turn",
        relation_posture=relation,
        perception_importance=perception_report,
        checked_at="2026-05-28T21:01:00+08:00",
        write_state=True,
    )

    comfort = next(candidate for candidate in ecology.candidates if candidate.intent_type == "comfort_quietly")
    state = read_intention_ecology_state(tmp_path)
    state_text = (tmp_path / "memory/context/intention_ecology_state.md").read_text(encoding="utf-8")
    trace_text = (tmp_path / "runtime/intention_ecology_trace.jsonl").read_text(encoding="utf-8")
    assert ecology.perception_gap_signal == "repair_gap"
    assert "perception_repair_gap_visible_risk:+8" in ecology.perception_gap_bias
    assert ecology.proactive_candidate == "none"
    assert comfort.future_candidate == "none"
    assert "proactive_blocked_by_repair_gap" in comfort.reason
    assert state["perception_gap_signal"] == "repair_gap"
    assert "perception_gap:repair_gap" in ecology.notes
    assert raw_private not in state_text
    assert raw_private not in trace_text


def test_intention_ecology_perception_maintenance_gap_raises_task_claim_risk(tmp_path: Path) -> None:
    relation = {"scene": "technical_or_system_design", "initiative_allowed": "unchanged", "risk_level": "low"}
    baseline = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="please continue the bounded task",
        relation_posture=relation,
        checked_at="2026-05-28T21:02:00+08:00",
    )
    perception_report = {
        "status": "pass",
        "metrics": {
            "latest_gap_type": "maintenance_gap",
            "latest_future_effect": "verify_restart_need_before_next_runtime_claim",
            "latest_event_ref": "sha256:maintenance-gap",
            "max_attention_weight": 75,
            "next_route_hint": "code_change_awareness",
        },
        "judgments": [
            {
                "event_id": "percevt-maintenance",
                "gap_type": "maintenance_gap",
                "suggested_route": "code_change_awareness",
                "future_effect": "verify_restart_need_before_next_runtime_claim",
                "attention_weight": 75,
                "evidence_ref": "sha256:maintenance-gap",
            }
        ],
    }

    ecology = evaluate_intention_ecology(
        tmp_path,
        _owner_payload(),
        user_text="please continue the bounded task",
        relation_posture=relation,
        perception_importance=perception_report,
        checked_at="2026-05-28T21:02:01+08:00",
        write_state=True,
    )

    baseline_task = next(candidate for candidate in baseline.candidates if candidate.intent_type == "do_bounded_task")
    maintenance_task = next(candidate for candidate in ecology.candidates if candidate.intent_type == "do_bounded_task")
    state = read_intention_ecology_state(tmp_path)
    assert ecology.perception_gap_signal == "maintenance_gap"
    assert "maintenance_gap_task_claim_risk:+6" in ecology.perception_gap_bias
    assert maintenance_task.risk_score == baseline_task.risk_score + 6
    assert "perception_maintenance_gap_verify_before_task_claim" in maintenance_task.reason
    assert "verify runtime/source state" in maintenance_task.visible_bias
    assert state["perception_gap_signal"] == "maintenance_gap"
