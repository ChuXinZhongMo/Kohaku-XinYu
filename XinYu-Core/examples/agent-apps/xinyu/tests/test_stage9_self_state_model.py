from __future__ import annotations

import json
from pathlib import Path

from xinyu_stage9_self_state_model import (
    STATE_REL,
    build_stage9_self_state_model,
    render_stage9_self_state_model,
    write_stage9_self_state_model_report,
    write_stage9_self_state_model_state,
    append_stage9_self_state_model_trace,
)
from xinyu_status import status_fields


RAW_PRIVATE = "RAW_STAGE9_PRIVATE_BODY_SHOULD_NOT_SURFACE_9021"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_ready_stage9_sources(root: Path) -> None:
    _write(
        root / "memory/context/stage8_memory_governance_state.md",
        """# Stage 8 Memory Governance State

- stage8_memory_governance_status: active_guarded
- stage8_memory_ready_for_stage9: true
- stage8_memory_governance_reason: memory_governance_backlog_and_learning_gate_clear
- stage8_next_step: stage9_self_state_model_can_start
- stage8_stable_profile_write: blocked_review_only_not_auto_apply
- stage8_owner_memory_write: blocked_owner_review_required
- stage8_stable_identity_profile_apply: blocked
- consciousness_claim: false
""",
    )
    _write(
        root / "memory/context/runtime_self_presence.md",
        f"""# Runtime Self Presence

- bridge_process: running
- current_turn_state: finished
- active_sessions: 1
- last_turn_status: ok
- last_source: owner_private
- last_user_preview: {RAW_PRIVATE}
- last_reply_preview: {RAW_PRIVATE}
""",
    )
    _write(
        root / "memory/context/intention_ecology_state.md",
        """# Intention Ecology State

- selected_intent: repair_relation
- selected_gate: current_turn_only
- action_level: visible_reply_only
- proactive_delivery: review_gated
- review_gated_future_count: 2
""",
    )
    _write(
        root / "memory/context/action_feedback_coverage_state.md",
        """# Action Feedback Coverage State

- latest_feedback_signal: qq_visible_reply_ack
- latest_feedback_surface: qq
- latest_lifecycle_status: acked
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

- research_needed: true
- focus_kind: research_collection_gap
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

- active: false
""",
    )


def test_stage9_self_state_model_builds_auditable_state_without_private_text(tmp_path: Path) -> None:
    _write_ready_stage9_sources(tmp_path)

    report = build_stage9_self_state_model(tmp_path)
    rendered = render_stage9_self_state_model(report)
    report_path = write_stage9_self_state_model_report(tmp_path, report)
    state_path = write_stage9_self_state_model_state(tmp_path, report, report_path=report_path)
    trace_path = append_stage9_self_state_model_trace(tmp_path, report)
    state = state_path.read_text(encoding="utf-8")
    trace = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])

    assert report["status"] == "active"
    assert report["ready_for_stage10"] is True
    assert report["model"]["current_task"] == "hold_research_handoff_as_internal_candidate"
    assert report["model"]["relation_posture"] == "owner_feedback_supported_current_style_trial"
    assert report["model"]["state_contract"] == "auditable_current_state_not_subjective_consciousness"
    assert report["boundaries"]["consciousness_claim"] is False
    assert "self_thought:research_collection_gap" in report["model"]["unfinished_intentions"]
    assert "generate_current_self_state_summary" in report["model"]["available_actions"]
    assert RAW_PRIVATE not in str(report)
    assert RAW_PRIVATE not in rendered
    assert RAW_PRIVATE not in report_path.read_text(encoding="utf-8")
    assert RAW_PRIVATE not in state
    assert RAW_PRIVATE not in json.dumps(trace, ensure_ascii=False)
    assert "stage9_ready_for_stage10: true" in state
    assert "raw_owner_text_in_state: false" in state
    assert "consciousness_claim: false" in state


def test_stage9_self_state_model_waits_for_stage8(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/stage8_memory_governance_state.md",
        "- stage8_memory_ready_for_stage9: false\n",
    )

    report = build_stage9_self_state_model(tmp_path)

    assert report["status"] == "waiting_for_stage8"
    assert report["ready_for_stage10"] is False
    assert report["model"]["current_task"] == "clear_stage8_memory_governance_before_self_state_model"
    assert "stage8_memory_governance_not_ready" in report["model"]["unfinished_intentions"]


def test_status_fields_exposes_stage9_self_state_model(tmp_path: Path) -> None:
    _write_ready_stage9_sources(tmp_path)

    fields = status_fields(tmp_path)

    assert fields["stage9_self_state_model_status"] == "active"
    assert fields["stage9_ready_for_stage10"] == "true"
    assert fields["stage9_state_contract"] == "auditable_current_state_not_subjective_consciousness"
    assert fields["stage9_raw_owner_text_in_state"] == "false"
    assert fields["stage9_consciousness_claim"] == "false"
