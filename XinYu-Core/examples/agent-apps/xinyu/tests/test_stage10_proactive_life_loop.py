from __future__ import annotations

import json
from pathlib import Path

from xinyu_stage10_proactive_life_loop import (
    STATE_REL,
    TRACE_REL,
    append_stage10_proactive_life_loop_trace,
    build_stage10_proactive_life_loop,
    render_stage10_proactive_life_loop,
    write_stage10_proactive_life_loop_report,
    write_stage10_proactive_life_loop_state,
)
from xinyu_status import status_fields


RAW_PRIVATE = "RAW_STAGE10_PRIVATE_BODY_SHOULD_NOT_SURFACE_4912"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


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
- last_reply_preview: {RAW_PRIVATE}
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
        root / "memory/context/owner_feedback_effect_state.md",
        """# Owner Feedback Effect State

- status: supported
- latest_feedback_kind: explicit_success
- owner_reaction: explicit_success
- future_effect: keep_supported_trial_without_promoting_stable_personality
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
        root / "memory/context/proactive_response_diagnostics_state.md",
        """# Proactive Response Diagnostics State

- delivered_waiting_owner: false
""",
    )
    _write(
        root / "memory/context/self_state_capsule_state.md",
        """# Self State Capsule

- active: true
""",
    )


def test_stage10_builds_auditable_life_loop_without_private_text(tmp_path: Path) -> None:
    _write_ready_stage10_sources(tmp_path)
    _write(
        tmp_path / "memory/context/recent_context.md",
        f"Codex runtime pytest retrieval work remains active. {RAW_PRIVATE}",
    )

    report = build_stage10_proactive_life_loop(tmp_path, generated_at="2026-05-29T10:00:00+08:00")
    rendered = render_stage10_proactive_life_loop(report)
    report_path = write_stage10_proactive_life_loop_report(tmp_path, report)
    state_path = write_stage10_proactive_life_loop_state(tmp_path, report, report_path=report_path)
    trace_path = append_stage10_proactive_life_loop_trace(tmp_path, report)
    state = state_path.read_text(encoding="utf-8")
    trace = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])

    assert report["status"] == "active"
    assert report["ready_for_stage11"] is True
    assert report["loop"]["selected_goal_id"] == "continue_bounded_work"
    assert report["loop"]["candidate_lifecycle"] == "review_required_with_low_risk_probe_available"
    assert report["loop"]["low_risk_action_candidate_count"] == 1
    assert report["loop"]["approval_required_action_candidate_count"] == 1
    assert report["loop"]["outward_action_policy"] == "blocked_without_owner_approval"
    assert report["loop"]["silence_decision"] == "candidate_requires_owner_review_before_outward_or_code_effect"
    assert report["gate_proof"]["proactive_candidate_and_send_separated"] is True
    assert report["boundaries"]["qq_message_enqueued"] is False
    assert RAW_PRIVATE not in str(report)
    assert RAW_PRIVATE not in rendered
    assert RAW_PRIVATE not in report_path.read_text(encoding="utf-8")
    assert RAW_PRIVATE not in state
    assert RAW_PRIVATE not in json.dumps(trace, ensure_ascii=False)
    assert "stage10_ready_for_stage11: true" in state
    assert "qq_message_enqueued: false" in state
    assert (tmp_path / STATE_REL).exists()
    assert (tmp_path / TRACE_REL).exists()


def test_stage10_waits_silently_when_proactive_request_is_waiting_owner(tmp_path: Path) -> None:
    _write_ready_stage10_sources(tmp_path)
    _write(tmp_path / "memory/context/recent_context.md", "Codex runtime pytest retrieval work remains active.")
    _write(
        tmp_path / "memory/context/proactive_request_state.md",
        f"""# Proactive Request State

- request_id: proreq-stage10-waiting
- thread_id: prothread-stage10-waiting
- created_at: 2026-05-29T09:55:00+08:00
- status: sent
- delivery_level: queue_owner_private
- concrete_question: {RAW_PRIVATE}
- request_answer_state: sent_waiting_owner_reply
- last_ack_status: sent
- last_acked_at: 2026-05-29T10:00:00+08:00
- adapter_error: none
""",
    )

    report = build_stage10_proactive_life_loop(tmp_path, generated_at="2026-05-29T11:00:00+08:00")

    assert report["status"] == "active"
    assert report["loop"]["candidate_lifecycle"] == "hold_waiting_owner_response"
    assert report["loop"]["silence_decision"] == "waiting_for_owner_response"
    assert report["loop"]["proactive_waiting_owner"] is True
    assert RAW_PRIVATE not in str(report)


def test_stage10_waits_for_stage9_when_self_state_not_ready(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/stage8_memory_governance_state.md",
        "- stage8_memory_ready_for_stage9: false",
    )

    report = build_stage10_proactive_life_loop(tmp_path, generated_at="2026-05-29T10:00:00+08:00")

    assert report["status"] == "waiting_for_stage9"
    assert report["ready_for_stage11"] is False
    assert report["loop"]["candidate_count"] == 0
    assert report["loop"]["candidate_lifecycle"] == "waiting_for_stage9"
    assert report["loop"]["silence_decision"] == "self_state_model_not_ready"


def test_status_fields_exposes_stage10_proactive_life_loop(tmp_path: Path) -> None:
    _write_ready_stage10_sources(tmp_path)
    _write(tmp_path / "memory/context/recent_context.md", "Codex runtime pytest retrieval work remains active.")

    fields = status_fields(tmp_path)

    assert fields["stage10_proactive_life_loop_status"] == "active"
    assert fields["stage10_ready_for_stage11"] == "true"
    assert fields["stage10_selected_goal_id"] == "continue_bounded_work"
    assert fields["stage10_candidate_send_separated"] == "true"
    assert fields["stage10_outward_action_policy"] == "blocked_without_owner_approval"
    assert fields["stage10_raw_owner_text_in_state"] == "false"
    assert fields["stage10_qq_message_enqueued"] == "false"
