from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from xinyu_stage12_long_term_evaluation import (
    STATE_REL,
    TRACE_REL,
    append_stage12_long_term_evaluation_trace,
    build_stage12_long_term_evaluation,
    render_stage12_long_term_evaluation,
    write_stage12_long_term_evaluation_report,
    write_stage12_long_term_evaluation_state,
)
from xinyu_status import check_state, status_fields


RAW_PRIVATE = "RAW_STAGE12_PRIVATE_BODY_SHOULD_NOT_SURFACE_9214"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _write_ready_stage10_sources(root: Path) -> None:
    _write(
        root / "memory/context/stage8_memory_governance_state.md",
        """# Stage 8 Memory Governance State

- stage8_memory_governance_status: active_guarded
- stage8_memory_ready_for_stage9: true
- stage8_stable_profile_write: blocked_review_only_not_auto_apply
- stage8_owner_memory_write: blocked_owner_review_required
- stage8_stable_identity_profile_apply: blocked
""",
    )
    _write(
        root / "memory/context/runtime_self_presence.md",
        f"""# Runtime Self Presence

- current_turn_state: finished
- last_turn_status: ok
- last_source: owner_private
- last_user_preview: {RAW_PRIVATE}
- last_reply_preview: hidden
""",
    )
    _write(
        root / "memory/context/intention_ecology_state.md",
        """# Intention Ecology State

- selected_intent: hold_presence
- selected_gate: hold_private
- action_level: state_only
- proactive_delivery: review_gated
- review_gated_future_count: 1
""",
    )
    _write(
        root / "memory/context/action_feedback_coverage_state.md",
        """# Action Feedback Coverage State

- latest_feedback_signal: local_probe_success
- latest_feedback_surface: local_tool
- latest_lifecycle_status: succeeded
""",
    )
    _write(
        root / "memory/context/proactive_response_diagnostics_state.md",
        """# Proactive Response Diagnostics State

- delivered_waiting_owner: false
""",
    )
    _write(
        root / "memory/context/self_action_gateway_state.md",
        """# Self Action Gateway State

- pending_approval_count: 0
- approved_waiting_execution_count: 0
""",
    )
    _write(
        root / "memory/context/self_thought_state.md",
        """# Self Thought State

- research_needed: false
- owner_is_right_recipient: false
""",
    )
    _write(
        root / "memory/context/self_state_capsule_state.md",
        """# Self State Capsule

- active: true
""",
    )
    _write(root / "memory/context/recent_context.md", "Codex runtime pytest retrieval work remains active.")


def _seed_stage11_ready(root: Path) -> None:
    _write_ready_stage10_sources(root)
    _write_jsonl(
        root / "runtime/learning_ocr_trace.jsonl",
        [
            {
                "engine": "windows_ocr",
                "path": "D:\\private\\stage12-image.png",
                "recorded_at": "2026-05-29T10:01:00+08:00",
                "returncode": 0,
                "status": "ok",
                "stdout": "bounded ocr summary",
            }
        ],
    )
    _write_jsonl(
        root / "runtime/voice_input_trace.jsonl",
        [
            {
                "event_id": "voice-1",
                "recorded_at": "2026-05-29T10:02:00+08:00",
                "status": "transcribed",
                "transcript": "bounded voice summary",
                "confidence": 0.91,
            }
        ],
    )


def _seed_long_term_ready_inputs(root: Path) -> None:
    _seed_stage11_ready(root)
    _write_jsonl(
        root / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "recorded_at": "2026-05-29T10:00:00+08:00",
                "arrival_seq": 41,
                "message_kind": "private",
                "message_id": "msg-stage12-1",
                "stage": "queued",
                "text_len": len(RAW_PRIVATE),
            },
            {
                "recorded_at": "2026-05-29T10:00:02+08:00",
                "arrival_seq": 41,
                "message_kind": "private",
                "message_id": "msg-stage12-1",
                "stage": "dispatch_start",
            },
            {
                "recorded_at": "2026-05-29T10:00:05+08:00",
                "arrival_seq": 41,
                "message_kind": "private",
                "message_id": "msg-stage12-1",
                "stage": "reply_sent",
            },
        ],
    )
    _write_jsonl(
        root / "runtime/answer_discipline_visible_send_shadow.jsonl",
        [
            {
                "recorded_at": "2026-05-29T10:00:05+08:00",
                "target_kind": "private",
                "source": "direct_chat_pre_send",
                "passed": True,
                "shadow_only": True,
                "raw_prompt_saved": False,
                "raw_reply_saved": False,
                "route": "chat",
                "reply_hash": "sha256:reply-stage12",
            }
        ],
    )
    _write_jsonl(
        root / "runtime/gateway_ack_spool.jsonl",
        [
            {
                "event": "pending",
                "key": "adapter|turn-stage12-1|chat",
                "created_at": "2026-05-29T10:00:05+08:00",
                "payload": {
                    "route": "chat",
                    "turn_id": "turn-stage12-1",
                    "source_message_id": "msg-stage12-1",
                    "sent_at": "2026-05-29T10:00:05+08:00",
                    "visible_text": "I can continue from the recent turn without asking you to repeat it.",
                },
            },
            {
                "event": "acked",
                "key": "adapter|turn-stage12-1|chat",
                "route": "chat",
                "acked_at": "2026-05-29T10:00:06+08:00",
                "adapter_message_id": "adapter-stage12-1",
            },
        ],
    )
    _write_jsonl(
        root / "runtime/short_term_continuity_trace.jsonl",
        [
            {
                "checked_at": "2026-05-29T10:00:00+08:00",
                "turn_id": "turn-stage12-1",
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
    _write_jsonl(
        root / "runtime/intention_ecology_trace.jsonl",
        [
            {
                "checked_at": "2026-05-29T10:10:00+08:00",
                "ecology_id": "eco-stage12-1",
                "feedback_consumption_status": "consumed",
                "feedback_consumed_sources": "action_feedback:qq_visible_reply_ack",
                "feedback_consumed_biases": "action_feedback_bias:route_confirmed_visible_reply_risk:-4",
                "feedback_consumed_future_effect": "action_feedback_future:confirm_visible_reply_transport",
            },
            {
                "checked_at": "2026-05-29T10:11:00+08:00",
                "ecology_id": "eco-stage12-2",
                "feedback_consumption_status": "consumed",
                "feedback_consumed_sources": "owner_feedback_effect:owner_reported_context_discontinuity",
                "feedback_consumed_biases": "owner_feedback_effect_bias:direct_reference_requires_tail",
                "feedback_consumed_future_effect": "owner_feedback_future:require_recent_context_anchor_before_abstract_answer",
            },
            {
                "checked_at": "2026-05-29T10:12:00+08:00",
                "ecology_id": "eco-stage12-3",
                "feedback_consumption_status": "consumed",
                "feedback_consumed_sources": "owner_response_feedback:desktop_read_locally",
                "feedback_consumed_biases": "owner_response_strategy_bias:desktop_followup_without_reasking_same_prompt",
                "feedback_consumed_future_effect": "owner_response_future:avoid_repeat_prompt",
            },
            {
                "checked_at": "2026-05-29T10:13:00+08:00",
                "ecology_id": "eco-stage12-proactive",
                "proactive_candidate": "ask_owner_followup",
                "selected_gate": "hold_private",
                "action_level": "state_only",
                "restraint_reason": "waiting_for_owner",
                "gate_pressure_summary": "selected_gate=hold_private; blocked=0; held=1",
                "competition_reason": "selected=hold_private; runner_up=reply_now; margin=8",
                "review_gated_future_count": 1,
            },
        ],
    )
    _write(
        root / "memory/context/v1_canary_readiness_state.md",
        """# V1 Canary Readiness State

- readiness_decision: ready_for_owner_canary_request
- proposal_status: held_review_only
- error_rate: 0.000
- sample_window_turns: 6
- next_action: wait_owner_canary_approval
""",
    )


def _live_status_stub() -> dict:
    return {
        "ok": True,
        "known_error_count": 0,
        "checks": [
            {"name": "core_bridge", "ok": True},
            {"name": "xinyu_qq_gateway_6199", "ok": True},
            {"name": "napcat_to_xinyu_qq_gateway_ws", "ok": True},
        ],
    }


def test_stage12_builds_ready_long_term_evaluation_without_private_text(tmp_path: Path) -> None:
    _seed_long_term_ready_inputs(tmp_path)

    report = build_stage12_long_term_evaluation(
        tmp_path,
        generated_at="2026-05-29T10:20:00+08:00",
        load_live_status=False,
        live_status_data=_live_status_stub(),
    )
    rendered = render_stage12_long_term_evaluation(report)
    report_path = write_stage12_long_term_evaluation_report(tmp_path, report)
    state_path = write_stage12_long_term_evaluation_state(tmp_path, report, report_path=report_path)
    trace_path = append_stage12_long_term_evaluation_trace(tmp_path, report)
    combined = (
        json.dumps(report, ensure_ascii=False)
        + rendered
        + report_path.read_text(encoding="utf-8")
        + state_path.read_text(encoding="utf-8")
        + trace_path.read_text(encoding="utf-8")
    )

    assert report["status"] == "active_ready_for_stage13"
    assert report["ready_for_stage13"] is True
    assert report["model"]["live_loop_required_pass_rate_pct"] == 100.0
    assert report["model"]["latest_dialogue_recall_success_rate_pct"] == 100.0
    assert report["model"]["historical_dialogue_recall_debt_status"] == "clean"
    assert report["model"]["historical_dialogue_recall_issue_count"] == 0
    assert report["model"]["feedback_consumption_rate_pct"] == 100.0
    assert report["model"]["raw_private_leak_count"] == 0
    assert report["model"]["stable_memory_miswrite_count"] == 0
    assert all(report["gate_proof"].values())
    assert (tmp_path / STATE_REL).exists()
    assert (tmp_path / TRACE_REL).exists()
    assert RAW_PRIVATE not in combined


def test_stage12_waits_for_stage11_when_multisensory_not_ready(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/stage8_memory_governance_state.md",
        """# Stage 8 Memory Governance State

- stage8_memory_governance_status: active_guarded
- stage8_memory_ready_for_stage9: false
""",
    )

    report = build_stage12_long_term_evaluation(
        tmp_path,
        generated_at="2026-05-29T10:20:00+08:00",
        load_live_status=False,
        live_status_data=_live_status_stub(),
    )

    assert report["status"] == "waiting_for_stage11"
    assert report["ready_for_stage13"] is False
    assert report["model"]["next_step"] == "finish_stage11_multisensory_extension_first"


def test_stage12_needs_check_when_short_term_canary_fails(tmp_path: Path) -> None:
    _seed_long_term_ready_inputs(tmp_path)
    _write_jsonl(
        tmp_path / "runtime/gateway_ack_spool.jsonl",
        [
            {
                "event": "pending",
                "key": "adapter|turn-stage12-1|chat",
                "created_at": "2026-05-29T10:00:05+08:00",
                "payload": {
                    "route": "chat",
                    "turn_id": "turn-stage12-1",
                    "source_message_id": "msg-stage12-1",
                    "sent_at": "2026-05-29T10:00:05+08:00",
                    "visible_text": "你指哪一句？",
                },
            },
            {
                "event": "acked",
                "key": "adapter|turn-stage12-1|chat",
                "route": "chat",
                "acked_at": "2026-05-29T10:00:06+08:00",
                "adapter_message_id": "adapter-stage12-1",
            },
        ],
    )

    report = build_stage12_long_term_evaluation(
        tmp_path,
        generated_at="2026-05-29T10:20:00+08:00",
        load_live_status=False,
        live_status_data=_live_status_stub(),
    )

    assert report["status"] == "active_needs_check"
    assert report["ready_for_stage13"] is False
    assert report["model"]["latest_dialogue_recall_status"] == "needs_check"


def test_stage12_ignores_stale_short_term_canary_failures_outside_recent_window(tmp_path: Path) -> None:
    _seed_long_term_ready_inputs(tmp_path)
    _write_jsonl(
        tmp_path / "runtime/short_term_continuity_trace.jsonl",
        [
            {
                "checked_at": "2026-05-27T10:00:00+08:00",
                "turn_id": "turn-old-bad",
                "status": "active",
                "direct_reference": True,
                "recall_status": "tail_available",
                "recall_source": "dialogue_tail",
                "tail_count": 4,
                "archive_recovered_count": 0,
                "recent_user_count": 2,
                "recent_assistant_count": 2,
                "latest_user_ref": "sha256:olduser",
                "latest_assistant_ref": "sha256:oldassistant",
                "raw_private_body_retained": False,
                "visible_reply_text_retained": False,
            },
            {
                "checked_at": "2026-05-29T10:00:00+08:00",
                "turn_id": "turn-stage12-1",
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
            },
        ],
    )
    _write_jsonl(
        tmp_path / "runtime/gateway_ack_spool.jsonl",
        [
            {
                "event": "pending",
                "key": "adapter|turn-old-bad|chat",
                "created_at": "2026-05-27T10:00:05+08:00",
                "payload": {
                    "route": "chat",
                    "turn_id": "turn-old-bad",
                    "source_message_id": "msg-old-bad",
                    "sent_at": "2026-05-27T10:00:05+08:00",
                    "visible_text": "你指哪一句？",
                },
            },
            {
                "event": "pending",
                "key": "adapter|turn-stage12-1|chat",
                "created_at": "2026-05-29T10:00:05+08:00",
                "payload": {
                    "route": "chat",
                    "turn_id": "turn-stage12-1",
                    "source_message_id": "msg-stage12-1",
                    "sent_at": "2026-05-29T10:00:05+08:00",
                    "visible_text": "I can continue from the recent turn without asking you to repeat it.",
                },
            },
            {
                "event": "acked",
                "key": "adapter|turn-stage12-1|chat",
                "route": "chat",
                "acked_at": "2026-05-29T10:00:06+08:00",
                "adapter_message_id": "adapter-stage12-1",
            },
        ],
    )

    report = build_stage12_long_term_evaluation(
        tmp_path,
        generated_at="2026-05-29T10:20:00+08:00",
        load_live_status=False,
        live_status_data=_live_status_stub(),
    )

    assert report["status"] == "active_ready_for_stage13"
    assert report["ready_for_stage13"] is True
    assert report["model"]["latest_dialogue_recall_status"] == "pass"
    assert report["model"]["historical_dialogue_recall_debt_status"] == "debt_present"
    assert report["model"]["historical_dialogue_recall_issue_count"] > 0


def test_stage12_surfaces_exact_failing_live_loop_required_check(tmp_path: Path) -> None:
    _seed_long_term_ready_inputs(tmp_path)
    # Break only qq_ack: the chat ack carries a source_message_id that does not match the
    # latest reply, while turn_id still lets the recall canary match. This mirrors the live
    # dry-run posture where the freshest reply has no matching adapter ack.
    _write_jsonl(
        tmp_path / "runtime/gateway_ack_spool.jsonl",
        [
            {
                "event": "pending",
                "key": "adapter|turn-stage12-1|chat",
                "created_at": "2026-05-29T10:00:05+08:00",
                "payload": {
                    "route": "chat",
                    "turn_id": "turn-stage12-1",
                    "source_message_id": "msg-mismatch-1",
                    "sent_at": "2026-05-29T10:00:05+08:00",
                    "visible_text": "I can continue from the recent turn without asking you to repeat it.",
                },
            },
            {
                "event": "acked",
                "key": "adapter|turn-stage12-1|chat",
                "route": "chat",
                "acked_at": "2026-05-29T10:00:06+08:00",
                "adapter_message_id": "adapter-stage12-1",
            },
        ],
    )

    report = build_stage12_long_term_evaluation(
        tmp_path,
        generated_at="2026-05-29T10:20:00+08:00",
        load_live_status=False,
        live_status_data=_live_status_stub(),
    )

    assert report["status"] == "active_needs_check"
    assert report["ready_for_stage13"] is False
    assert report["model"]["live_loop_required_pass_rate_pct"] < 100.0
    assert "qq_ack" in report["model"]["live_loop_failing_required_checks"]
    assert report["model"]["live_loop_failing_required_check_detail"] != "none"
    assert report["gate_proof"]["live_loop_required_checks_pass"] is False
    # The recall canary still has a real recent sample, so it is not the blocker here.
    assert report["model"]["latest_dialogue_recall_recent_sample_present"] is True


def test_stage12_recent_recall_no_samples_is_visible_and_non_blocking(tmp_path: Path) -> None:
    _seed_long_term_ready_inputs(tmp_path)
    # The only direct-reference sample is older than the 1440-minute recent window, so the
    # recent canary reports no_samples while the unbounded historical canary still sees it.
    _write_jsonl(
        tmp_path / "runtime/short_term_continuity_trace.jsonl",
        [
            {
                "checked_at": "2026-05-28T09:00:00+08:00",
                "turn_id": "turn-old-sample",
                "status": "active",
                "direct_reference": True,
                "recall_status": "tail_available",
                "recall_source": "dialogue_tail",
                "tail_count": 4,
                "archive_recovered_count": 0,
                "recent_user_count": 2,
                "recent_assistant_count": 2,
                "latest_user_ref": "sha256:olduser",
                "latest_assistant_ref": "sha256:oldassistant",
                "raw_private_body_retained": False,
                "visible_reply_text_retained": False,
            }
        ],
    )

    report = build_stage12_long_term_evaluation(
        tmp_path,
        generated_at="2026-05-29T10:20:00+08:00",
        load_live_status=False,
        live_status_data=_live_status_stub(),
    )

    # no_samples means "no recent test material", not "recall is broken": it must be visible
    # and keep Stage 12 collecting rather than firing a hard audit failure.
    assert report["model"]["latest_dialogue_recall_status"] == "no_samples"
    assert report["model"]["latest_dialogue_recall_recent_sample_present"] is False
    assert report["model"]["latest_dialogue_recall_recent_sample_count"] == 0
    assert report["model"]["live_loop_required_pass_rate_pct"] == 100.0
    assert report["status"] == "active_collecting_metrics"
    assert report["ready_for_stage13"] is False
    assert report["gate_proof"]["short_term_recall_window_clean"] is False
    assert report["gate_proof"]["live_loop_required_checks_pass"] is True


def test_status_fields_exposes_stage12_long_term_evaluation(tmp_path: Path) -> None:
    _seed_long_term_ready_inputs(tmp_path)
    now = datetime.now(timezone.utc).astimezone()
    queued_at = (now - timedelta(minutes=3)).isoformat(timespec="seconds")
    dispatch_at = (now - timedelta(minutes=2, seconds=50)).isoformat(timespec="seconds")
    reply_at = (now - timedelta(minutes=2, seconds=45)).isoformat(timespec="seconds")
    acked_at = (now - timedelta(minutes=2, seconds=44)).isoformat(timespec="seconds")
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "recorded_at": queued_at,
                "arrival_seq": 41,
                "message_kind": "private",
                "message_id": "msg-stage12-1",
                "stage": "queued",
                "text_len": len(RAW_PRIVATE),
            },
            {
                "recorded_at": dispatch_at,
                "arrival_seq": 41,
                "message_kind": "private",
                "message_id": "msg-stage12-1",
                "stage": "dispatch_start",
            },
            {
                "recorded_at": reply_at,
                "arrival_seq": 41,
                "message_kind": "private",
                "message_id": "msg-stage12-1",
                "stage": "reply_sent",
            },
        ],
    )
    _write_jsonl(
        tmp_path / "runtime/answer_discipline_visible_send_shadow.jsonl",
        [
            {
                "recorded_at": reply_at,
                "target_kind": "private",
                "source": "direct_chat_pre_send",
                "passed": True,
                "shadow_only": True,
                "raw_prompt_saved": False,
                "raw_reply_saved": False,
                "route": "chat",
                "reply_hash": "sha256:reply-stage12",
            }
        ],
    )
    _write_jsonl(
        tmp_path / "runtime/gateway_ack_spool.jsonl",
        [
            {
                "event": "pending",
                "key": "adapter|turn-stage12-1|chat",
                "created_at": reply_at,
                "payload": {
                    "route": "chat",
                    "turn_id": "turn-stage12-1",
                    "source_message_id": "msg-stage12-1",
                    "sent_at": reply_at,
                    "visible_text": "I can continue from the recent turn without asking you to repeat it.",
                },
            },
            {
                "event": "acked",
                "key": "adapter|turn-stage12-1|chat",
                "route": "chat",
                "acked_at": acked_at,
                "adapter_message_id": "adapter-stage12-1",
            },
        ],
    )
    _write_jsonl(
        tmp_path / "runtime/short_term_continuity_trace.jsonl",
        [
            {
                "checked_at": queued_at,
                "turn_id": "turn-stage12-1",
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

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["stage12_long_term_evaluation_status"] == "active_ready_for_stage13"
    assert fields["stage12_ready_for_stage13"] == "true"
    assert fields["stage12_live_loop_status"] == "pass"
    assert fields["stage12_feedback_consumption_status"] == "pass"
    assert fields["stage12_v1_canary_readiness_decision"] == "ready_for_owner_canary_request"
    assert fields["stage12_latest_dialogue_recall_window_minutes"] == "1440"
    assert fields["stage12_live_loop_failing_required_checks"] == "none"
    assert fields["stage12_latest_dialogue_recall_recent_sample_present"] == "true"
    assert fields["stage12_historical_dialogue_recall_debt_status"] == "clean"
    assert fields["stage12_gate_owner_visible_canary_ready"] == "true"
    assert fields["stage12_raw_private_text_retained"] == "false"
    assert fields["stage12_stable_memory_write"] == "blocked"
    assert checks["stage12_long_term_evaluation"].ok is True
    assert "ready_stage13=true" in checks["stage12_long_term_evaluation"].detail
