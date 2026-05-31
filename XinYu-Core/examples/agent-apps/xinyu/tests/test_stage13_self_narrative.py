from __future__ import annotations

import json
from pathlib import Path

from xinyu_stage13_self_narrative import (
    STATE_REL,
    TRACE_REL,
    append_stage13_self_narrative_trace,
    build_stage13_self_narrative,
    render_stage13_self_narrative,
    write_stage13_self_narrative_report,
    write_stage13_self_narrative_state,
)
from xinyu_status import check_state, status_fields


RAW_PRIVATE = "RAW_STAGE13_PRIVATE_BODY_SHOULD_NOT_SURFACE_7788"


def _stage12(ready: bool, *, debt_status: str = "debt_present", debt_count: int = 2) -> dict:
    return {
        "ready_for_stage13": ready,
        "model": {
            "historical_dialogue_recall_debt_status": debt_status,
            "historical_dialogue_recall_issue_count": debt_count,
        },
    }


def _decision_chain(**overrides) -> dict:
    chain = {
        "gate": "current_turn_only",
        "action_level": "visible_reply_only",
        "selected_candidate": "answer_current_turn",
        "internal_state": "answer_current_turn",
        "restraint_reason": "none",
        "proactive_candidate": "none",
        "competition_reason": "selected=answer_current_turn",
        "gate_pressure_summary": "selected_gate=current_turn_only; blocked=0; held=0",
        "owner_feedback_signal": "memory_mechanics_leak",
        "owner_feedback_future_effect": "avoid_memory_mechanics_in_visible_reply_unless_owner_requests_diagnostics",
        "action_feedback_signal": "qq_outbox_delivery_ack",
        "action_feedback_future_effect": "confirm_visible_reply_transport_for_next_turn",
        "owner_response_signal": "none",
        "owner_response_future_effect": "none",
    }
    chain.update(overrides)
    return {"status": "observed", "decision_chain": chain}


def _stage8_gov() -> dict:
    return {
        "status": "active_guarded",
        "stable_profile_write": "blocked_review_only_not_auto_apply",
        "owner_memory_write": "blocked_owner_review_required",
        "learning_trial_success_gate": "blocked",
        "learning_trial_validation_needed_success_count": 2,
        "learning_trial_validation_owner_action": "collect_2_more_same_trial_explicit_owner_success",
        "learning_trial_validation_active_key": "memory_mechanics_leak",
    }


def _owner_feedback() -> dict:
    return {
        "expression_strategy_bias": "avoid_memory_mechanics_in_visible_reply",
        "intention_bias": "visible_mechanism_leak_risk:+12",
    }


def _build(tmp_path: Path, *, ready: bool, decision_chain: dict | None = None, **kw) -> dict:
    return build_stage13_self_narrative(
        tmp_path,
        stage12_report=_stage12(ready, **kw),
        decision_chain_report=decision_chain or _decision_chain(),
        stage8_governance=_stage8_gov(),
        owner_feedback_effect_report=_owner_feedback(),
    )


def test_stage13_available_when_stage12_ready(tmp_path: Path) -> None:
    report = _build(tmp_path, ready=True)

    assert report["status"] == "active_available_for_self_narrative"
    assert report["available"] is True
    assert report["model"]["stage12_ready_for_stage13"] is True
    # Narrative is built only from verifiable evidence fields.
    assert report["model"]["feedback_influence_count"] == 2
    assert report["model"]["behavior_explanation"]["behavior_mode"] == "visible_reply"
    assert report["model"]["narrative_source"] == "verifiable_status_fields_only"
    # Historical recall debt is surfaced, never hidden.
    assert report["model"]["historical_recall_debt"]["status"] == "debt_present"
    assert report["model"]["historical_recall_debt"]["issue_count"] == 2
    assert report["boundaries"]["historical_recall_debt_hidden"] is False


def test_stage13_waits_when_stage12_not_ready(tmp_path: Path) -> None:
    report = _build(tmp_path, ready=False, debt_status="clean", debt_count=0)

    assert report["status"] == "waiting_for_stage12"
    assert report["available"] is False
    assert report["model"]["stage12_ready_for_stage13"] is False
    assert report["model"]["next_step"] == "finish_stage12_long_term_evaluation_before_self_narrative"


def test_stage13_never_claims_consciousness_or_fake_sensor(tmp_path: Path) -> None:
    report = _build(tmp_path, ready=True)
    rendered = render_stage13_self_narrative(report)
    boundaries = report["boundaries"]

    assert boundaries["consciousness_claim"] is False
    assert boundaries["dream_or_body_or_fake_sensor_claim"] is False
    assert report["model"]["stage13_contract"] == (
        "self_narrative_summarizes_verified_evidence_no_consciousness_claim"
    )
    assert "no consciousness claim" in rendered.lower()
    # The narrative must never contain dream/body/fake-sensor claims.
    for forbidden in ("梦境", "身体", "我有意识", "consciousness complete", "i am conscious"):
        assert forbidden not in rendered


def test_stage13_does_not_surface_raw_private_or_visible_reply_text(tmp_path: Path) -> None:
    # Even if an upstream field smuggles secret/path-like or private-looking text, the
    # narrative scrubs it and never echoes raw owner / visible-reply bodies.
    chain = _decision_chain(
        owner_feedback_future_effect=f"token={RAW_PRIVATE} /home/owner/secret.md keep this bias",
    )
    report = build_stage13_self_narrative(
        tmp_path,
        stage12_report=_stage12(True),
        decision_chain_report=chain,
        stage8_governance=_stage8_gov(),
        owner_feedback_effect_report=_owner_feedback(),
    )
    rendered = render_stage13_self_narrative(report)
    report_path = write_stage13_self_narrative_report(tmp_path, report)
    state_path = write_stage13_self_narrative_state(tmp_path, report, report_path=report_path)
    trace_path = append_stage13_self_narrative_trace(tmp_path, report)
    combined = (
        json.dumps(report, ensure_ascii=False)
        + rendered
        + report_path.read_text(encoding="utf-8")
        + state_path.read_text(encoding="utf-8")
        + trace_path.read_text(encoding="utf-8")
    )

    assert RAW_PRIVATE not in combined
    assert report["boundaries"]["raw_owner_text_retained"] is False
    assert report["boundaries"]["visible_reply_text_retained"] is False
    assert (tmp_path / STATE_REL).exists()
    assert (tmp_path / TRACE_REL).exists()


def test_stage13_records_stage8_guarded_state_not_promoted(tmp_path: Path) -> None:
    report = _build(tmp_path, ready=True)
    report_path = write_stage13_self_narrative_report(tmp_path, report)
    state = write_stage13_self_narrative_state(tmp_path, report, report_path=report_path).read_text(
        encoding="utf-8"
    )
    governance = report["model"]["memory_governance_state"]
    approved = report["model"]["approved_memory_or_strategy_influence"]

    # Stage 8 stays guarded and is written faithfully, not faked as a promoted memory.
    assert governance["stage8_status"] == "active_guarded"
    assert governance["memory_promoted_to_stable_fact"] is False
    assert governance["needed_same_trial_success_count"] == 2
    assert governance["requires_two_clean_same_trial_success"] is True
    assert governance["stable_profile_write"] == "blocked_review_only_not_auto_apply"
    # No stable memory is approved; only runtime bias influences behavior.
    assert approved["approved_stable_memory_count"] == 0
    assert approved["influence_kind"] == "runtime_strategy_bias_only_not_approved_stable_memory"
    # State file records guarded + not-promoted, and never claims promotion.
    assert "stage13_memory_governance_status: active_guarded" in state
    assert "stage13_memory_promoted_to_stable_fact: false" in state
    assert "stage13_needed_same_trial_success_count: 2" in state
    assert "stable_memory_write: blocked" in state


def test_status_exposes_stage13_waiting_when_stage12_not_ready(tmp_path: Path) -> None:
    # On a bare runtime, Stage 12 is not ready, so Stage 13 must report waiting (not available),
    # and the status check must still pass as a healthy report layer.
    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["stage13_self_narrative_status"] == "waiting_for_stage12"
    assert fields["stage13_available"] == "false"
    assert fields["stage13_consciousness_claim"] == "false"
    assert fields["stage13_dream_or_body_or_fake_sensor_claim"] == "false"
    assert fields["stage13_memory_promoted_to_stable_fact"] == "false"
    assert "stage13_self_narrative" in checks
    assert checks["stage13_self_narrative"].ok is True
    assert "waiting_for_stage12" in checks["stage13_self_narrative"].detail
