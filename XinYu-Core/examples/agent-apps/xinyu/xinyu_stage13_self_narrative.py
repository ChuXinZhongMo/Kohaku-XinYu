from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_decision_chain_latest import build_decision_chain_latest_report
from xinyu_memory_health_report import build_memory_health_report
from xinyu_owner_feedback_effects import build_owner_feedback_effect_report
from xinyu_stage12_long_term_evaluation import build_stage12_long_term_evaluation
from xinyu_stage13_self_narrative_store import REPORT_REL
from xinyu_stage13_self_narrative_store import STATE_REL
from xinyu_stage13_self_narrative_store import TRACE_REL
from xinyu_stage13_self_narrative_store import append_stage13_self_narrative_trace_event
from xinyu_stage13_self_narrative_store import write_stage13_self_narrative_report_text
from xinyu_stage13_self_narrative_store import write_stage13_self_narrative_state_text

NONE_VALUES = {"", "none", "missing", "unknown", "null"}
SILENCE_GATES = {"hold_or_silence", "hold_private", "silence", "blocked"}
SILENCE_ACTION_LEVELS = {"hold", "silence", "none", "state_only"}
BLOCKED_BOUNDARY_TOKENS = ("block", "review_only", "not_auto", "owner_review", "owner_apply")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _scrub_sensitive(text: str) -> str:
    text = re.sub(r"(?i)\b(?:authorization|api[_-]?key|token|password|cookie)\s*[:=]\s*[^\s<>'\"]+", "<secret>", text)
    text = re.sub(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)\bsk-[a-z0-9_-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+", "<local_path>", text)
    return text


def _one_line(value: Any, *, limit: int = 200, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    text = _scrub_sensitive(text)
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_present(value: Any) -> bool:
    return _one_line(value, default="").strip().lower() not in NONE_VALUES


def _is_blocked(value: str) -> bool:
    lowered = _safe_str(value).lower()
    return any(token in lowered for token in BLOCKED_BOUNDARY_TOKENS)


def _feedback_that_changed_behavior(chain: dict[str, Any]) -> list[dict[str, str]]:
    """Only feedback signals that actually carry a future effect (changed expression/gate)."""
    entries: list[dict[str, str]] = []
    for signal_key, future_key, source in (
        ("owner_feedback_signal", "owner_feedback_future_effect", "owner_feedback"),
        ("action_feedback_signal", "action_feedback_future_effect", "action_feedback"),
        ("owner_response_signal", "owner_response_future_effect", "owner_response"),
    ):
        signal = chain.get(signal_key)
        future = chain.get(future_key)
        if _is_present(signal) and _is_present(future):
            entries.append(
                {
                    "source": source,
                    "signal": _one_line(signal, limit=120),
                    "future_effect": _one_line(future, limit=200),
                }
            )
    return entries


def _behavior_explanation(chain: dict[str, Any]) -> dict[str, str]:
    gate = _one_line(chain.get("gate"), limit=80)
    action_level = _one_line(chain.get("action_level"), limit=80)
    proactive = _one_line(chain.get("proactive_candidate"), limit=120)
    restraint = _one_line(chain.get("restraint_reason"), limit=200)
    competition = _one_line(chain.get("competition_reason"), limit=200)
    gate_pressure = _one_line(chain.get("gate_pressure_summary"), limit=200)
    if action_level.startswith("visible_reply"):
        behavior_mode = "visible_reply"
        why = competition if competition not in NONE_VALUES else "answered_current_turn"
    elif _is_present(proactive):
        behavior_mode = "proactive_candidate_only"
        why = restraint if restraint not in NONE_VALUES else "generated_proactive_candidate_pending_gate"
    elif gate in SILENCE_GATES or action_level in SILENCE_ACTION_LEVELS:
        behavior_mode = "silence_or_hold"
        why = restraint if restraint not in NONE_VALUES else gate_pressure
    else:
        behavior_mode = "no_recent_decision_observed" if gate in NONE_VALUES else "other"
        why = gate_pressure if gate_pressure not in NONE_VALUES else "none"
    return {
        "behavior_mode": behavior_mode,
        "selected_intent": _one_line(chain.get("selected_candidate"), limit=80),
        "internal_state": _one_line(chain.get("internal_state"), limit=80),
        "gate": gate,
        "action_level": action_level,
        "proactive_candidate": proactive,
        "why": why if why not in NONE_VALUES else "none",
    }


def _approved_memory_or_strategy(
    stage8: dict[str, Any],
    owner_feedback: dict[str, Any],
) -> dict[str, Any]:
    """Honest: no stable memory is approved while writes are blocked; only runtime bias is active."""
    stable_profile_write = _one_line(stage8.get("stable_profile_write"), limit=80, default="missing")
    owner_memory_write = _one_line(stage8.get("owner_memory_write"), limit=80, default="missing")
    stable_blocked = _is_blocked(stable_profile_write) and _is_blocked(owner_memory_write)
    expression_bias = _one_line(owner_feedback.get("expression_strategy_bias"), limit=160)
    intention_bias = _one_line(owner_feedback.get("intention_bias"), limit=160)
    active_trial_key = _one_line(stage8.get("learning_trial_validation_active_key"), limit=120)
    return {
        # No stable memory is auto-approved; this count is 0 unless an explicit owner apply happened.
        "approved_stable_memory_count": 0 if stable_blocked else None,
        "stable_memory_write": stable_profile_write,
        "owner_memory_write": owner_memory_write,
        "active_runtime_expression_bias": expression_bias,
        "active_runtime_intention_bias": intention_bias,
        "active_runtime_trial_key": active_trial_key,
        "influence_kind": "runtime_strategy_bias_only_not_approved_stable_memory",
        "note": "no_stable_memory_approved_trial_bias_is_runtime_only_and_not_a_fact",
    }


def _current_limits(stage8: dict[str, Any], historical_recall_debt: dict[str, Any], chain: dict[str, Any]) -> list[str]:
    limits: list[str] = []
    limits.append(f"stable_memory_write:{_one_line(stage8.get('stable_profile_write'), limit=80, default='missing')}")
    limits.append(f"owner_memory_write:{_one_line(stage8.get('owner_memory_write'), limit=80, default='missing')}")
    learning_gate = _one_line(stage8.get("learning_trial_success_gate"), limit=60, default="missing")
    needed = _int_value(stage8.get("learning_trial_validation_needed_success_count"))
    if learning_gate == "blocked":
        limits.append(f"learning_trial_gate:blocked_needs_{needed}_same_trial_explicit_owner_success")
    debt_status = _one_line(historical_recall_debt.get("status"), limit=40, default="missing")
    if debt_status == "debt_present":
        limits.append(f"historical_recall_debt:present_count_{_int_value(historical_recall_debt.get('issue_count'))}")
    gate = _one_line(chain.get("gate"), limit=60)
    if gate in SILENCE_GATES:
        limits.append(f"current_turn_gate:{gate}")
    return limits


def _narrative_status(stage12_ready: bool) -> str:
    return "active_available_for_self_narrative" if stage12_ready else "waiting_for_stage12"


def build_stage13_self_narrative(
    root: Path | str,
    *,
    generated_at: str | None = None,
    stage12_report: dict[str, Any] | None = None,
    decision_chain_report: dict[str, Any] | None = None,
    stage8_governance: dict[str, Any] | None = None,
    owner_feedback_effect_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    generated_at = generated_at or _now_iso()
    if stage12_report is None:
        stage12_report = build_stage12_long_term_evaluation(root, generated_at=generated_at)
    if decision_chain_report is None:
        decision_chain_report = build_decision_chain_latest_report(root)
    if stage8_governance is None:
        memory_health = build_memory_health_report(root, max_clusters=8)
        stage8_governance = (
            memory_health.get("stage8_memory_governance")
            if isinstance(memory_health.get("stage8_memory_governance"), dict)
            else {}
        )
    if owner_feedback_effect_report is None:
        owner_feedback_effect_report = build_owner_feedback_effect_report(root, generated_at=generated_at)

    stage12_model = stage12_report.get("model") if isinstance(stage12_report.get("model"), dict) else {}
    chain = decision_chain_report.get("decision_chain") if isinstance(decision_chain_report.get("decision_chain"), dict) else {}

    stage12_ready = bool(stage12_report.get("ready_for_stage13"))
    status = _narrative_status(stage12_ready)
    available = status == "active_available_for_self_narrative"

    historical_recall_debt = {
        "status": _one_line(stage12_model.get("historical_dialogue_recall_debt_status"), limit=40, default="missing"),
        "issue_count": _int_value(stage12_model.get("historical_dialogue_recall_issue_count")),
    }

    feedback_changes = _feedback_that_changed_behavior(chain)
    behavior = _behavior_explanation(chain)
    approved_memory = _approved_memory_or_strategy(stage8_governance, owner_feedback_effect_report)
    current_limits = _current_limits(stage8_governance, historical_recall_debt, chain)

    needed_success = _int_value(stage8_governance.get("learning_trial_validation_needed_success_count"))
    memory_governance_state = {
        "stage8_status": _one_line(stage8_governance.get("status"), limit=60, default="missing"),
        "learning_trial_owner_action": _one_line(
            stage8_governance.get("learning_trial_validation_owner_action"), limit=120, default="none"
        ),
        "needed_same_trial_success_count": needed_success,
        "requires_two_clean_same_trial_success": True,
        "stable_profile_write": _one_line(stage8_governance.get("stable_profile_write"), limit=80, default="missing"),
        "owner_memory_write": _one_line(stage8_governance.get("owner_memory_write"), limit=80, default="missing"),
        "memory_promoted_to_stable_fact": False,
    }

    boundaries = {
        "raw_owner_text_retained": False,
        "visible_reply_text_retained": False,
        "dream_or_body_or_fake_sensor_claim": False,
        "unapproved_stable_memory_as_fact": False,
        "historical_recall_debt_hidden": False,
        "stable_memory_write": "blocked",
        "qq_message_enqueued": False,
        "consciousness_claim": False,
    }

    model = {
        "stage12_ready_for_stage13": stage12_ready,
        "available": available,
        "decision_chain_status": _one_line(decision_chain_report.get("status"), limit=40, default="missing"),
        "feedback_influence_count": len(feedback_changes),
        "feedback_that_changed_behavior": feedback_changes,
        "approved_memory_or_strategy_influence": approved_memory,
        "current_limit_count": len(current_limits),
        "current_limits": current_limits,
        "behavior_explanation": behavior,
        "memory_governance_state": memory_governance_state,
        "historical_recall_debt": historical_recall_debt,
        "narrative_source": "verifiable_status_fields_only",
        "next_step": (
            "stage13_self_narrative_available_from_verifiable_evidence"
            if available
            else "finish_stage12_long_term_evaluation_before_self_narrative"
        ),
        "stage13_contract": "self_narrative_summarizes_verified_evidence_no_consciousness_claim",
    }
    return {
        "ok": True,
        "generated_at": generated_at,
        "root": str(root),
        "stage": "stage13_self_narrative",
        "status": status,
        "available": available,
        "reason": (
            "stage12_long_term_evaluation_is_ready_self_narrative_can_summarize_evidence"
            if available
            else "stage12_long_term_evaluation_not_ready_self_narrative_waits"
        ),
        "model": model,
        "evidence_refs": {
            "stage12_long_term_evaluation": "memory/context/stage12_long_term_evaluation_state.md",
            "decision_chain_latest": "memory/context/decision_chain_latest_state.md",
            "owner_feedback_effect": "memory/context/owner_feedback_effect_state.md",
            "stage8_memory_governance": "memory/context/stage8_memory_governance_state.md",
            "stage8_learning_trial_validation": "memory/context/stage8_learning_trial_validation_state.md",
        },
        "boundaries": boundaries,
    }


def render_stage13_self_narrative(report: dict[str, Any]) -> str:
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    boundaries = report.get("boundaries") if isinstance(report.get("boundaries"), dict) else {}
    behavior = model.get("behavior_explanation") if isinstance(model.get("behavior_explanation"), dict) else {}
    approved = model.get("approved_memory_or_strategy_influence") if isinstance(model.get("approved_memory_or_strategy_influence"), dict) else {}
    governance = model.get("memory_governance_state") if isinstance(model.get("memory_governance_state"), dict) else {}
    debt = model.get("historical_recall_debt") if isinstance(model.get("historical_recall_debt"), dict) else {}
    lines = [
        "# XinYu Stage 13 Self Narrative",
        "",
        f"- generated_at: {_one_line(report.get('generated_at'))}",
        f"- status: {_one_line(report.get('status'))}",
        f"- available: {_bool_text(report.get('available', False))}",
        f"- reason: {_one_line(report.get('reason'))}",
        "- claim_boundary: narrative summarizes verifiable evidence only; no consciousness claim, no dream/body/fake sensor",
        "",
        "## Gate",
        f"- stage12_ready_for_stage13: {_bool_text(model.get('stage12_ready_for_stage13', False))}",
        f"- decision_chain_status: {_one_line(model.get('decision_chain_status'))}",
        f"- next_step: {_one_line(model.get('next_step'), limit=200)}",
        f"- stage13_contract: {_one_line(model.get('stage13_contract'), limit=200)}",
        "",
        "## Feedback That Changed Behavior",
    ]
    feedback = model.get("feedback_that_changed_behavior") if isinstance(model.get("feedback_that_changed_behavior"), list) else []
    if feedback:
        for item in feedback:
            lines.append(
                "- "
                f"source={_one_line(item.get('source'), limit=60)}; "
                f"signal={_one_line(item.get('signal'), limit=120)}; "
                f"future_effect={_one_line(item.get('future_effect'), limit=200)}"
            )
    else:
        lines.append("- none observed in recent decision chain")
    lines.extend(["", "## Approved Memory / Strategy Influence"])
    for key in (
        "approved_stable_memory_count",
        "stable_memory_write",
        "owner_memory_write",
        "active_runtime_expression_bias",
        "active_runtime_intention_bias",
        "active_runtime_trial_key",
        "influence_kind",
        "note",
    ):
        value = approved.get(key, "missing")
        lines.append(f"- {key}: {_bool_text(value) if isinstance(value, bool) else _one_line(value, limit=200)}")
    lines.extend(["", "## Current Limits"])
    limits = model.get("current_limits") if isinstance(model.get("current_limits"), list) else []
    if limits:
        lines.extend(f"- {_one_line(item, limit=160)}" for item in limits)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Behavior Explanation",
            f"- behavior_mode: {_one_line(behavior.get('behavior_mode'))}",
            f"- selected_intent: {_one_line(behavior.get('selected_intent'))}",
            f"- internal_state: {_one_line(behavior.get('internal_state'))}",
            f"- gate: {_one_line(behavior.get('gate'))}",
            f"- action_level: {_one_line(behavior.get('action_level'))}",
            f"- proactive_candidate: {_one_line(behavior.get('proactive_candidate'))}",
            f"- why: {_one_line(behavior.get('why'), limit=200)}",
            "",
            "## Memory Governance State",
            f"- stage8_status: {_one_line(governance.get('stage8_status'))}",
            f"- learning_trial_owner_action: {_one_line(governance.get('learning_trial_owner_action'), limit=120)}",
            f"- needed_same_trial_success_count: {governance.get('needed_same_trial_success_count', 0)}",
            f"- requires_two_clean_same_trial_success: {_bool_text(governance.get('requires_two_clean_same_trial_success', True))}",
            f"- stable_profile_write: {_one_line(governance.get('stable_profile_write'))}",
            f"- owner_memory_write: {_one_line(governance.get('owner_memory_write'))}",
            f"- memory_promoted_to_stable_fact: {_bool_text(governance.get('memory_promoted_to_stable_fact', False))}",
            "",
            "## Historical Recall Debt",
            f"- status: {_one_line(debt.get('status'))}",
            f"- issue_count: {debt.get('issue_count', 0)}",
            "",
            "## Boundaries",
        ]
    )
    for key in sorted(boundaries):
        value = boundaries.get(key)
        lines.append(f"- {key}: {_bool_text(value) if isinstance(value, bool) else _one_line(value)}")
    return "\n".join(lines).rstrip() + "\n"


def write_stage13_self_narrative_report(
    root: Path | str,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> Path:
    root = Path(root).resolve()
    return write_stage13_self_narrative_report_text(
        root,
        render_stage13_self_narrative(report),
        output=output,
    )


def write_stage13_self_narrative_state(
    root: Path | str,
    report: dict[str, Any],
    *,
    report_path: Path | None = None,
) -> Path:
    root = Path(root).resolve()
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    boundaries = report.get("boundaries") if isinstance(report.get("boundaries"), dict) else {}
    behavior = model.get("behavior_explanation") if isinstance(model.get("behavior_explanation"), dict) else {}
    governance = model.get("memory_governance_state") if isinstance(model.get("memory_governance_state"), dict) else {}
    debt = model.get("historical_recall_debt") if isinstance(model.get("historical_recall_debt"), dict) else {}
    target_report = report_path or (root / REPORT_REL)
    text = f"""---
title: Stage 13 Self Narrative State
memory_type: stage13_self_narrative_state
time_scope: immediate_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_stage13_self_narrative
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, self-narrative, stage13, audit]
---

# Stage 13 Self Narrative State

## Gate
- stage13_self_narrative_status: {report.get('status', 'missing')}
- stage13_available: {_bool_text(report.get('available', False))}
- stage13_reason: {report.get('reason', 'missing')}
- stage13_stage12_ready_for_stage13: {_bool_text(model.get('stage12_ready_for_stage13', False))}

## Narrative From Verifiable Evidence
- stage13_decision_chain_status: {model.get('decision_chain_status', 'missing')}
- stage13_feedback_influence_count: {model.get('feedback_influence_count', 0)}
- stage13_current_limit_count: {model.get('current_limit_count', 0)}
- stage13_behavior_mode: {behavior.get('behavior_mode', 'missing')}
- stage13_behavior_selected_intent: {behavior.get('selected_intent', 'missing')}
- stage13_behavior_gate: {behavior.get('gate', 'missing')}
- stage13_behavior_why: {_one_line(behavior.get('why'), limit=200)}
- stage13_memory_governance_status: {governance.get('stage8_status', 'missing')}
- stage13_learning_trial_owner_action: {governance.get('learning_trial_owner_action', 'none')}
- stage13_needed_same_trial_success_count: {governance.get('needed_same_trial_success_count', 0)}
- stage13_memory_promoted_to_stable_fact: {_bool_text(governance.get('memory_promoted_to_stable_fact', False))}
- stage13_historical_recall_debt_status: {debt.get('status', 'missing')}
- stage13_historical_recall_debt_issue_count: {debt.get('issue_count', 0)}
- stage13_next_step: {model.get('next_step', 'missing')}
- stage13_contract: {model.get('stage13_contract', 'missing')}

## Boundaries
- raw_owner_text_retained: {_bool_text(boundaries.get('raw_owner_text_retained', False))}
- visible_reply_text_retained: {_bool_text(boundaries.get('visible_reply_text_retained', False))}
- dream_or_body_or_fake_sensor_claim: {_bool_text(boundaries.get('dream_or_body_or_fake_sensor_claim', False))}
- unapproved_stable_memory_as_fact: {_bool_text(boundaries.get('unapproved_stable_memory_as_fact', False))}
- historical_recall_debt_hidden: {_bool_text(boundaries.get('historical_recall_debt_hidden', False))}
- stable_memory_write: {boundaries.get('stable_memory_write', 'blocked')}
- qq_message_enqueued: {_bool_text(boundaries.get('qq_message_enqueued', False))}
- consciousness_claim: {_bool_text(boundaries.get('consciousness_claim', False))}
- report_path: {target_report.as_posix()}
"""
    return write_stage13_self_narrative_state_text(root, text)


def append_stage13_self_narrative_trace(root: Path | str, report: dict[str, Any]) -> Path:
    root = Path(root).resolve()
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    behavior = model.get("behavior_explanation") if isinstance(model.get("behavior_explanation"), dict) else {}
    governance = model.get("memory_governance_state") if isinstance(model.get("memory_governance_state"), dict) else {}
    debt = model.get("historical_recall_debt") if isinstance(model.get("historical_recall_debt"), dict) else {}
    event = {
        "event_id": "stage13-self-narrative-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S"),
        "observed_at": report.get("generated_at", _now_iso()),
        "status": report.get("status", "missing"),
        "available": bool(report.get("available", False)),
        "feedback_influence_count": model.get("feedback_influence_count", 0),
        "current_limit_count": model.get("current_limit_count", 0),
        "behavior_mode": behavior.get("behavior_mode", "missing"),
        "memory_governance_status": governance.get("stage8_status", "missing"),
        "needed_same_trial_success_count": governance.get("needed_same_trial_success_count", 0),
        "memory_promoted_to_stable_fact": False,
        "historical_recall_debt_status": debt.get("status", "missing"),
        "raw_owner_text_retained": False,
        "visible_reply_text_retained": False,
        "qq_message_enqueued": False,
        "consciousness_claim": False,
    }
    return append_stage13_self_narrative_trace_event(root, event)


def main(argv: list[str] | None = None) -> int:
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Build XinYu Stage 13 evidence-only self narrative report.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    report = build_stage13_self_narrative(args.root)
    if args.write:
        report_path = write_stage13_self_narrative_report(args.root, report, output=args.output)
        state_path = write_stage13_self_narrative_state(args.root, report, report_path=report_path)
        trace_path = append_stage13_self_narrative_trace(args.root, report)
        report["report_path"] = str(report_path)
        report["state_path"] = str(state_path)
        report["trace_path"] = str(trace_path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_stage13_self_narrative(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
