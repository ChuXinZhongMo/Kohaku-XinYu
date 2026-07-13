from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_action_feedback_coverage import build_action_feedback_coverage_report
from xinyu_bridge_values import as_int, compact_text, safe_str
from xinyu_owner_feedback_effects_store import append_owner_feedback_effect_trace_event
from xinyu_owner_feedback_effects_store import owner_feedback_effect_state_path
from xinyu_owner_feedback_effects_store import read_owner_feedback_effect_state_text
from xinyu_owner_feedback_effects_store import write_owner_feedback_effect_report_text
from xinyu_owner_feedback_effects_store import write_owner_feedback_effect_state_text
from xinyu_state_io import read_text

LEARNING_STATE_REL = Path("memory/self/learning_closed_loop_state.md")
LEARNING_TRACE_REL = Path("runtime/learning_closed_loop_trace.jsonl")
EXPRESSION_STATE_REL = Path("memory/self/expression_self_learning_state.md")
POST_REPLY_TRACE_REL = Path("runtime/post_reply_self_observation_trace.jsonl")
PROACTIVE_REQUEST_STATE_REL = Path("memory/context/proactive_request_state.md")

NONE_VALUES = {"", "missing", "none", "unknown", "null", "false"}
OWNER_IGNORE_AFTER_MINUTES = 180
REALTIME_REPAIR_PRESSURE_CAP_THRESHOLD = 8
STYLE_REPAIR_PRESSURE_CAPPED_EFFECT = {
    "expression_strategy_bias": "style_repair_pressure_capped_keep_current_turn_anchor",
    "intention_bias": "repair_relation_visible_risk:-2",
    "future_effect": "style_repair_direct_only_ordinary_chat_keeps_current_anchor",
}

EFFECTS_BY_KIND = {
    "owner_reported_template_voice_failure": {
        "expression_strategy_bias": "avoid_template_or_feedback_processing_phrase",
        "intention_bias": "repair_relation_visible_risk:-6",
        "future_effect": "prefer_concrete_replacement_line_over_feedback_processing",
    },
    "owner_reported_context_discontinuity": {
        "expression_strategy_bias": "anchor_recent_context_before_reply",
        "intention_bias": "direct_reference_requires_tail",
        "future_effect": "require_recent_context_anchor_before_abstract_answer",
    },
    "owner_reported_time_fact_error": {
        "expression_strategy_bias": "state_exact_date_when_time_sensitive",
        "intention_bias": "time_claim_needs_runtime_date",
        "future_effect": "verify_runtime_date_before_time_sensitive_reply",
    },
    "owner_reported_learning_empty_loop": {
        "expression_strategy_bias": "prefer_replayable_case_over_summary",
        "intention_bias": "memory_candidate_requires_recallable_effect",
        "future_effect": "only_keep_learning_that_changes_a_future_case",
    },
    "post_reply_template_voice_risk": {
        "expression_strategy_bias": "avoid_template_voice_after_reply",
        "intention_bias": "repair_relation_visible_risk:-4",
        "future_effect": "shorten_next_style_repair_into_a_live_line",
    },
    "post_reply_mechanical_self_state_risk": {
        "expression_strategy_bias": "hide_backend_mechanics_answer_first_person_state",
        "intention_bias": "self_state_mechanical_risk:+10",
        "future_effect": "answer_self_state_without_backend_mechanics",
    },
    "post_reply_over_explained_risk": {
        "expression_strategy_bias": "shorten_next_reply_to_one_or_two_lines",
        "intention_bias": "long_answer_risk:+6",
        "future_effect": "compress_next_reply_before_analysis",
    },
    "post_reply_missed_emotional_grounding": {
        "expression_strategy_bias": "ground_emotion_before_task_or_analysis",
        "intention_bias": "comfort_current_turn_value:+8",
        "future_effect": "ground_relation_pressure_before_continuing_task",
    },
    "post_reply_low_information_ack_risk": {
        "expression_strategy_bias": "replace_bare_ack_with_one_specific_current_anchor",
        "intention_bias": "low_information_ack_risk:+8",
        "future_effect": "answer_with_one_current_anchor_instead_of_bare_ack",
    },
    "visible_expression_leak": {
        "expression_strategy_bias": "avoid_visible_mechanism_or_template_leak",
        "intention_bias": "visible_mechanism_leak_risk:+12",
        "future_effect": "block_mechanism_terms_in_casual_owner_chat",
    },
    "visible_mechanism_or_template_leak": {
        "expression_strategy_bias": "avoid_visible_mechanism_or_template_leak",
        "intention_bias": "visible_mechanism_leak_risk:+12",
        "future_effect": "block_mechanism_terms_in_casual_owner_chat",
    },
    "memory_mechanics_leak": {
        "expression_strategy_bias": "avoid_memory_mechanics_in_visible_reply",
        "intention_bias": "visible_mechanism_leak_risk:+12",
        "future_effect": "avoid_memory_mechanics_in_visible_reply_unless_owner_requests_diagnostics",
    },
    "explicit_success": {
        "expression_strategy_bias": "keep_current_style_trial",
        "intention_bias": "current_trial_risk:-3",
        "future_effect": "keep_supported_trial_without_promoting_stable_personality",
    },
}

RESPONSE_EFFECTS_BY_SIGNAL = {
    "desktop_read_locally": {
        "owner_response_strategy_bias": "desktop_followup_without_reasking_same_prompt",
        "owner_response_intention_bias": "proactive_repeat_risk:+4",
        "owner_response_future_effect": "prefer_desktop_thread_followup_without_reasking_same_prompt",
    },
    "desktop_dismissed": {
        "owner_response_strategy_bias": "lower_same_request_priority",
        "owner_response_intention_bias": "proactive_future_block:+10",
        "owner_response_future_effect": "lower_same_request_priority_until_new_evidence",
    },
    "desktop_owner_replied": {
        "owner_response_strategy_bias": "route_owner_reply_back_to_source_thread",
        "owner_response_intention_bias": "current_thread_value:+6",
        "owner_response_future_effect": "route_owner_reply_back_to_source_thread",
    },
    "desktop_approved_qq": {
        "owner_response_strategy_bias": "allow_one_bounded_qq_enqueue_if_gates_pass",
        "owner_response_intention_bias": "one_time_qq_permission:+8",
        "owner_response_future_effect": "allow_one_bounded_qq_enqueue_if_other_gates_pass",
    },
    "desktop_qq_enqueue_failed": {
        "owner_response_strategy_bias": "verify_desktop_or_qq_delivery_before_future_request",
        "owner_response_intention_bias": "proactive_delivery_risk:+12",
        "owner_response_future_effect": "check_desktop_or_qq_delivery_before_future_request",
    },
    "owner_no_response_timeout": {
        "owner_response_strategy_bias": "enter_observation_and_reduce_repeat_request",
        "owner_response_intention_bias": "proactive_repeat_risk:+12",
        "owner_response_future_effect": "lower_active_request_frequency_until_new_owner_evidence",
    },
}


def build_owner_feedback_effect_report(root: Path, *, generated_at: str | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    generated_at = generated_at or _now_iso()
    learning = _parse_fields(read_text(root / LEARNING_STATE_REL))
    expression = _parse_fields(read_text(root / EXPRESSION_STATE_REL))
    proactive_request = _parse_fields(read_text(root / PROACTIVE_REQUEST_STATE_REL))
    latest_learning_trace = _latest_jsonl_row(root / LEARNING_TRACE_REL)
    latest_post_reply = _latest_jsonl_row(root / POST_REPLY_TRACE_REL)
    action_coverage = build_action_feedback_coverage_report(root, generated_at=generated_at)
    latest_kind = _latest_feedback_kind(learning, expression, latest_learning_trace, latest_post_reply)
    realtime_pressure_status, realtime_pressure_reason = _realtime_pressure_status(learning, latest_kind)
    effect = _effect_for_kind(latest_kind, realtime_pressure_status=realtime_pressure_status)
    owner_response = _owner_response_effect(
        action_coverage,
        proactive_request,
        generated_at=generated_at,
    )
    status = _status_for(learning, latest_kind)
    if status == "no_signal" and owner_response["owner_response_signal"] not in NONE_VALUES:
        status = "response_active"
    owner_reaction = _owner_reaction_for(learning, latest_kind)
    repair_count = as_int(learning.get("repair_count"), 0)
    success_count = as_int(learning.get("success_count"), 0)
    success_streak = as_int(learning.get("success_streak"), 0)
    trial_success_count = as_int(learning.get("trial_success_count"), success_count)
    trial_success_streak = as_int(learning.get("trial_success_streak"), success_streak)
    latest_success_trial_key = _one_line(learning.get("latest_success_trial_key"), "none")
    success_evidence_status = _one_line(learning.get("success_evidence_status"), "none")
    promotion_signal = _one_line(learning.get("promotion_signal"), "false")
    active_trial_habit = _one_line(learning.get("active_trial_habit"), "none", limit=220)
    expected_next_behavior = _one_line(learning.get("expected_next_behavior"), "none", limit=220)
    expression_strategy_bias = _one_line(effect.get("expression_strategy_bias"), "none")
    intention_bias = _one_line(effect.get("intention_bias"), "none")
    future_effect = _one_line(effect.get("future_effect"), "none")
    feedback_event_ref = _feedback_event_ref(learning, latest_learning_trace, latest_post_reply)

    active_feedback = latest_kind not in NONE_VALUES
    active_feedback_ok = not active_feedback or (
        expression_strategy_bias not in NONE_VALUES
        and intention_bias not in NONE_VALUES
        and future_effect not in NONE_VALUES
    )
    active_response = owner_response["owner_response_signal"] not in NONE_VALUES
    active_response_ok = not active_response or (
        owner_response["owner_response_strategy_bias"] not in NONE_VALUES
        and owner_response["owner_response_intention_bias"] not in NONE_VALUES
        and owner_response["owner_response_future_effect"] not in NONE_VALUES
    )
    report = {
        "ok": active_feedback_ok and active_response_ok,
        "status": status,
        "generated_at": generated_at,
        "root": str(root),
        "latest_feedback_kind": latest_kind,
        "owner_reaction": owner_reaction,
        "active_trial_habit": active_trial_habit,
        "expected_next_behavior": expected_next_behavior,
        "expression_strategy_bias": expression_strategy_bias,
        "intention_bias": intention_bias,
        "repair_pressure_count": repair_count,
        "success_count": success_count,
        "success_streak": success_streak,
        "trial_success_count": trial_success_count,
        "trial_success_streak": trial_success_streak,
        "latest_success_trial_key": latest_success_trial_key,
        "success_evidence_status": success_evidence_status,
        "promotion_signal": promotion_signal,
        "future_effect": future_effect,
        "realtime_pressure_status": realtime_pressure_status,
        "realtime_pressure_reason": realtime_pressure_reason,
        "feedback_event_ref": feedback_event_ref,
        "owner_response_signal": owner_response["owner_response_signal"],
        "owner_response_source": owner_response["owner_response_source"],
        "owner_response_strategy_bias": owner_response["owner_response_strategy_bias"],
        "owner_response_intention_bias": owner_response["owner_response_intention_bias"],
        "owner_response_future_effect": owner_response["owner_response_future_effect"],
        "owner_response_event_ref": owner_response["owner_response_event_ref"],
        "source_snapshot": {
            "learning_status": _one_line(learning.get("status"), "missing"),
            "learning_owner_reaction": _one_line(learning.get("last_owner_reaction"), "missing"),
            "learning_failure_kind": _one_line(learning.get("latest_failure_kind"), "none"),
            "expression_failure_kind": _one_line(expression.get("failure_kind"), "none"),
            "post_reply_signal": _post_reply_signal(latest_post_reply),
            "desktop_feedback_signal": owner_response["owner_response_signal"],
            "desktop_feedback_source": owner_response["owner_response_source"],
        },
        "privacy": {
            "raw_owner_text_retained": False,
            "visible_reply_text_retained": False,
            "raw_owner_text_in_report": False,
            "visible_reply_text_in_report": False,
            "stable_personality_write": "blocked",
        },
        "notes": _notes(
            status,
            latest_kind,
            expression_strategy_bias,
            intention_bias,
            realtime_pressure_status=realtime_pressure_status,
            realtime_pressure_reason=realtime_pressure_reason,
            owner_response_signal=owner_response["owner_response_signal"],
            owner_response_intention_bias=owner_response["owner_response_intention_bias"],
        ),
    }
    return report


def read_owner_feedback_effect_state(root: Path) -> dict[str, str]:
    text = read_owner_feedback_effect_state_text(root)
    if not text:
        return {"status": "missing", "latest_feedback_kind": "none", "intention_bias": "none"}
    return _parse_fields(text)


def write_owner_feedback_effect(
    root: Path,
    report: dict[str, Any],
    *,
    output: Path | None = None,
    write_report: bool = True,
) -> dict[str, str]:
    root = Path(root).resolve()
    paths: dict[str, str] = {}
    if write_report:
        report_path = write_owner_feedback_effect_report_text(
            root,
            render_owner_feedback_effect_report(report),
            output=output,
        )
        paths["report_path"] = str(report_path)
    _write_state(root, report, report_path=paths.get("report_path", "not_written"))
    _append_trace(root, report)
    paths["state_path"] = str(owner_feedback_effect_state_path(root))
    return paths


def render_owner_feedback_effect_report(report: dict[str, Any]) -> str:
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    source = report.get("source_snapshot") if isinstance(report.get("source_snapshot"), dict) else {}
    lines = [
        "# XinYu Owner Feedback Effect",
        "",
        f"- generated_at: {report.get('generated_at', 'unknown')}",
        f"- status: {report.get('status', 'unknown')}",
        f"- result: {'pass' if report.get('ok') else 'needs_check'}",
        "- claim_boundary: owner feedback changes scoring and expression strategy only; does not claim consciousness",
        "",
        "## Current Effect",
        f"- latest_feedback_kind: {report.get('latest_feedback_kind', 'none')}",
        f"- owner_reaction: {report.get('owner_reaction', 'none')}",
        f"- expression_strategy_bias: {report.get('expression_strategy_bias', 'none')}",
        f"- intention_bias: {report.get('intention_bias', 'none')}",
        f"- future_effect: {report.get('future_effect', 'none')}",
        f"- realtime_pressure_status: {report.get('realtime_pressure_status', 'normal')}",
        f"- realtime_pressure_reason: {report.get('realtime_pressure_reason', 'none')}",
        f"- owner_response_signal: {report.get('owner_response_signal', 'none')}",
        f"- owner_response_source: {report.get('owner_response_source', 'none')}",
        f"- owner_response_strategy_bias: {report.get('owner_response_strategy_bias', 'none')}",
        f"- owner_response_intention_bias: {report.get('owner_response_intention_bias', 'none')}",
        f"- owner_response_future_effect: {report.get('owner_response_future_effect', 'none')}",
        f"- owner_response_event_ref: {report.get('owner_response_event_ref', 'none')}",
        f"- repair_pressure_count: {report.get('repair_pressure_count', 0)}",
        f"- success_count: {report.get('success_count', 0)}",
        f"- success_streak: {report.get('success_streak', 0)}",
        f"- trial_success_count: {report.get('trial_success_count', 0)}",
        f"- trial_success_streak: {report.get('trial_success_streak', 0)}",
        f"- latest_success_trial_key: {report.get('latest_success_trial_key', 'none')}",
        f"- success_evidence_status: {report.get('success_evidence_status', 'none')}",
        f"- promotion_signal: {report.get('promotion_signal', 'false')}",
        f"- feedback_event_ref: {report.get('feedback_event_ref', 'none')}",
        "",
        "## Source Snapshot",
    ]
    for key in (
        "learning_status",
        "learning_owner_reaction",
        "learning_failure_kind",
        "expression_failure_kind",
        "post_reply_signal",
        "desktop_feedback_signal",
        "desktop_feedback_source",
    ):
        lines.append(f"- {key}: {source.get(key, 'missing')}")
    lines.extend(["", "## Privacy Boundary"])
    for key, value in privacy.items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Notes"])
    notes = report.get("notes") if isinstance(report.get("notes"), list) else []
    lines.extend(f"- {note}" for note in notes) if notes else lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def _write_state(root: Path, report: dict[str, Any], *, report_path: str) -> None:
    text = f"""---
title: Owner Feedback Effect State
memory_type: owner_feedback_effect_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_owner_feedback_effects
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, owner-feedback, expression-strategy, scoring]
---

# Owner Feedback Effect State

## Current Effect
- status: {report.get('status', 'unknown')}
- checked_at: {report.get('generated_at', 'unknown')}
- latest_feedback_kind: {report.get('latest_feedback_kind', 'none')}
- owner_reaction: {report.get('owner_reaction', 'none')}
- active_trial_habit: {report.get('active_trial_habit', 'none')}
- expected_next_behavior: {report.get('expected_next_behavior', 'none')}
- expression_strategy_bias: {report.get('expression_strategy_bias', 'none')}
- intention_bias: {report.get('intention_bias', 'none')}
- repair_pressure_count: {report.get('repair_pressure_count', 0)}
- success_count: {report.get('success_count', 0)}
- success_streak: {report.get('success_streak', 0)}
- trial_success_count: {report.get('trial_success_count', 0)}
- trial_success_streak: {report.get('trial_success_streak', 0)}
- latest_success_trial_key: {report.get('latest_success_trial_key', 'none')}
- success_evidence_status: {report.get('success_evidence_status', 'none')}
- promotion_signal: {report.get('promotion_signal', 'false')}
- future_effect: {report.get('future_effect', 'none')}
- realtime_pressure_status: {report.get('realtime_pressure_status', 'normal')}
- realtime_pressure_reason: {report.get('realtime_pressure_reason', 'none')}
- feedback_event_ref: {report.get('feedback_event_ref', 'none')}
- owner_response_signal: {report.get('owner_response_signal', 'none')}
- owner_response_source: {report.get('owner_response_source', 'none')}
- owner_response_strategy_bias: {report.get('owner_response_strategy_bias', 'none')}
- owner_response_intention_bias: {report.get('owner_response_intention_bias', 'none')}
- owner_response_future_effect: {report.get('owner_response_future_effect', 'none')}
- owner_response_event_ref: {report.get('owner_response_event_ref', 'none')}

## Boundaries
- report_path: {report_path}
- raw_owner_text_retained: false
- visible_reply_text_retained: false
- raw_owner_text_in_report: false
- visible_reply_text_in_report: false
- stable_personality_write: blocked
"""
    write_owner_feedback_effect_state_text(root, text)


def _append_trace(root: Path, report: dict[str, Any]) -> None:
    row = {
        "generated_at": report.get("generated_at", ""),
        "status": report.get("status", ""),
        "ok": bool(report.get("ok")),
        "latest_feedback_kind": report.get("latest_feedback_kind", "none"),
        "owner_reaction": report.get("owner_reaction", "none"),
        "expression_strategy_bias": report.get("expression_strategy_bias", "none"),
        "intention_bias": report.get("intention_bias", "none"),
        "future_effect": report.get("future_effect", "none"),
        "realtime_pressure_status": report.get("realtime_pressure_status", "normal"),
        "realtime_pressure_reason": report.get("realtime_pressure_reason", "none"),
        "repair_pressure_count": report.get("repair_pressure_count", 0),
        "success_count": report.get("success_count", 0),
        "success_streak": report.get("success_streak", 0),
        "trial_success_count": report.get("trial_success_count", 0),
        "trial_success_streak": report.get("trial_success_streak", 0),
        "latest_success_trial_key": report.get("latest_success_trial_key", "none"),
        "success_evidence_status": report.get("success_evidence_status", "none"),
        "feedback_event_ref": report.get("feedback_event_ref", "none"),
        "owner_response_signal": report.get("owner_response_signal", "none"),
        "owner_response_source": report.get("owner_response_source", "none"),
        "owner_response_strategy_bias": report.get("owner_response_strategy_bias", "none"),
        "owner_response_intention_bias": report.get("owner_response_intention_bias", "none"),
        "owner_response_future_effect": report.get("owner_response_future_effect", "none"),
        "owner_response_event_ref": report.get("owner_response_event_ref", "none"),
        "raw_owner_text_retained": False,
        "visible_reply_text_retained": False,
        "stable_personality_write": "blocked",
    }
    append_owner_feedback_effect_trace_event(root, row)


def _effect_for_kind(latest_kind: str, *, realtime_pressure_status: str) -> dict[str, str]:
    if (
        latest_kind == "owner_reported_template_voice_failure"
        and realtime_pressure_status == "capped_direct_failure_only"
    ):
        return STYLE_REPAIR_PRESSURE_CAPPED_EFFECT
    return EFFECTS_BY_KIND.get(latest_kind, {})


def _realtime_pressure_status(learning: dict[str, str], latest_kind: str) -> tuple[str, str]:
    if latest_kind != "owner_reported_template_voice_failure":
        return "normal", "none"
    repair_count = as_int(learning.get("repair_count"), 0)
    success_streak = as_int(learning.get("success_streak"), 0)
    trial_success_streak = as_int(learning.get("trial_success_streak"), success_streak)
    success_evidence = _one_line(learning.get("success_evidence_status"), "none")
    if (
        repair_count >= REALTIME_REPAIR_PRESSURE_CAP_THRESHOLD
        and trial_success_streak < 2
        and success_evidence != "same_trial_explicit_owner_success"
    ):
        reason = f"repair_pressure_overloaded:{repair_count},same_key_success_streak:{trial_success_streak}"
        return "capped_direct_failure_only", reason
    return "normal", "none"


def _latest_feedback_kind(
    learning: dict[str, str],
    expression: dict[str, str],
    latest_learning_trace: dict[str, Any],
    latest_post_reply: dict[str, Any],
) -> str:
    if _one_line(learning.get("last_owner_reaction"), "none") == "explicit_success":
        return "explicit_success"
    if latest_learning_trace.get("success") is True:
        return "explicit_success"
    failure_kind = _one_line(learning.get("latest_failure_kind"), "none")
    if failure_kind not in NONE_VALUES:
        return failure_kind
    post_reply_signal = _post_reply_signal(latest_post_reply)
    if post_reply_signal not in NONE_VALUES:
        return post_reply_signal
    expression_failure = _one_line(expression.get("failure_kind"), "none")
    if expression_failure not in NONE_VALUES:
        return expression_failure
    return "none"


def _status_for(learning: dict[str, str], latest_kind: str) -> str:
    if latest_kind in NONE_VALUES:
        return "no_signal"
    if latest_kind == "explicit_success" or _one_line(learning.get("status"), "none") == "trial_supported":
        return "supported"
    return "active"


def _owner_reaction_for(learning: dict[str, str], latest_kind: str) -> str:
    reaction = _one_line(learning.get("last_owner_reaction"), "none")
    if reaction not in NONE_VALUES:
        return reaction
    if latest_kind == "explicit_success":
        return "explicit_success"
    if latest_kind.startswith("owner_reported_"):
        return "repair_pressure"
    if latest_kind.startswith("post_reply_"):
        return "post_reply_self_observation"
    if latest_kind in {"visible_expression_leak", "visible_mechanism_or_template_leak"}:
        return "guard_or_expression_failure"
    return "none"


def _owner_response_effect(
    action_coverage: dict[str, Any],
    proactive_request: dict[str, str],
    *,
    generated_at: str,
) -> dict[str, str]:
    surfaces = action_coverage.get("surfaces") if isinstance(action_coverage.get("surfaces"), dict) else {}
    desktop = surfaces.get("desktop") if isinstance(surfaces.get("desktop"), dict) else {}
    signal = _one_line(desktop.get("feedback_signal"), "none")
    source = "desktop_feedback" if signal in RESPONSE_EFFECTS_BY_SIGNAL else "none"
    event_source = desktop.get("evidence_ref") or desktop.get("checked_at") or ""

    if signal not in RESPONSE_EFFECTS_BY_SIGNAL and _proactive_request_ignored(
        proactive_request,
        generated_at=generated_at,
    ):
        signal = "owner_no_response_timeout"
        source = "proactive_request_timeout"
        event_source = (
            proactive_request.get("request_id")
            or proactive_request.get("thread_id")
            or proactive_request.get("created_at")
            or proactive_request.get("checked_at")
            or proactive_request.get("last_acked_at")
            or ""
        )

    effect = RESPONSE_EFFECTS_BY_SIGNAL.get(signal, {})
    return {
        "owner_response_signal": signal if signal in RESPONSE_EFFECTS_BY_SIGNAL else "none",
        "owner_response_source": source,
        "owner_response_strategy_bias": _one_line(effect.get("owner_response_strategy_bias"), "none"),
        "owner_response_intention_bias": _one_line(effect.get("owner_response_intention_bias"), "none"),
        "owner_response_future_effect": _one_line(effect.get("owner_response_future_effect"), "none"),
        "owner_response_event_ref": _content_ref(event_source),
    }


def _proactive_request_ignored(fields: dict[str, str], *, generated_at: str) -> bool:
    answer_state = _one_line(fields.get("request_answer_state"), "none").lower()
    last_ack = _one_line(fields.get("last_ack_status"), "none").lower()
    state_status = _one_line(fields.get("status"), "none").lower()
    if answer_state in {"not_requested", "none", "missing", "unknown", "owner_replied", "dismissed", "read_locally"}:
        return False
    waiting_answer = answer_state in {
        "pending",
        "sent_waiting_owner_reply",
        "waiting_owner_reply",
        "sent_waiting_feedback",
    }
    delivered_request = last_ack in {"sent", "queued", "delivered", "acked", "success"} or state_status in {
        "sent",
        "claimed",
        "delivered",
    }
    if not waiting_answer or not delivered_request:
        return False
    timestamp = (
        fields.get("last_acked_at")
        or fields.get("created_at")
        or fields.get("checked_at")
        or fields.get("evaluated_at")
        or fields.get("updated_at")
        or ""
    )
    age_minutes = _age_minutes(timestamp, generated_at)
    return age_minutes is not None and age_minutes >= OWNER_IGNORE_AFTER_MINUTES


def _post_reply_signal(row: dict[str, Any]) -> str:
    scores = row.get("scores") if isinstance(row.get("scores"), dict) else {}
    notes = row.get("notes") if isinstance(row.get("notes"), list) else []
    if "post_reply_mechanical_risk" in notes or scores.get("mechanical_risk") == "high":
        return "post_reply_mechanical_self_state_risk"
    if "post_reply_template_voice_risk" in notes or scores.get("template_risk") in {"medium", "high"}:
        return "post_reply_template_voice_risk"
    if "post_reply_over_explained_risk" in notes or scores.get("over_explained_risk") in {"medium", "high"}:
        return "post_reply_over_explained_risk"
    if "post_reply_missed_emotional_grounding" in notes or scores.get("emotional_grounding") == "missing":
        return "post_reply_missed_emotional_grounding"
    if "post_reply_low_information_ack_risk" in notes or scores.get("low_information_ack_risk") == "high":
        return "post_reply_low_information_ack_risk"
    return "none"


def _feedback_event_ref(
    learning: dict[str, str],
    latest_learning_trace: dict[str, Any],
    latest_post_reply: dict[str, Any],
) -> str:
    source = (
        learning.get("latest_event_id")
        or latest_learning_trace.get("event_id")
        or latest_post_reply.get("observed_at")
        or ""
    )
    text = safe_str(source).strip()
    if not text or text in NONE_VALUES:
        return "none"
    return _content_ref(text)


def _notes(
    status: str,
    latest_kind: str,
    expression_strategy_bias: str,
    intention_bias: str,
    *,
    realtime_pressure_status: str,
    realtime_pressure_reason: str,
    owner_response_signal: str,
    owner_response_intention_bias: str,
) -> list[str]:
    notes: list[str] = []
    if status == "no_signal":
        notes.append("no_active_owner_feedback_effect")
    else:
        notes.append(f"owner_feedback_effect:{latest_kind}")
    if expression_strategy_bias not in NONE_VALUES:
        notes.append(f"expression_strategy:{expression_strategy_bias}")
    if intention_bias not in NONE_VALUES:
        notes.append(f"intention_bias:{intention_bias}")
    if realtime_pressure_status != "normal":
        notes.append(f"realtime_pressure:{realtime_pressure_status}")
    if realtime_pressure_reason not in NONE_VALUES:
        notes.append(f"realtime_pressure_reason:{realtime_pressure_reason}")
    if owner_response_signal not in NONE_VALUES:
        notes.append(f"owner_response_feedback:{owner_response_signal}")
    if owner_response_intention_bias not in NONE_VALUES:
        notes.append(f"owner_response_bias:{owner_response_intention_bias}")
    notes.append("stable_personality_write_blocked")
    return notes


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _latest_jsonl_row(path: Path, *, max_lines: int = 400) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return {}
    for line in reversed(lines[-max(1, int(max_lines)) :]):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return {}


def _age_minutes(start: Any, end: Any) -> float | None:
    start_dt = _parse_timestamp(start)
    end_dt = _parse_timestamp(end)
    if start_dt is None or end_dt is None:
        return None
    if start_dt.tzinfo is not None and end_dt.tzinfo is not None:
        end_dt = end_dt.astimezone(start_dt.tzinfo)
    elif start_dt.tzinfo is not None and end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=start_dt.tzinfo)
    elif start_dt.tzinfo is None and end_dt.tzinfo is not None:
        start_dt = start_dt.replace(tzinfo=end_dt.tzinfo)
    return max(0.0, (end_dt - start_dt).total_seconds() / 60.0)


def _parse_timestamp(value: Any) -> datetime | None:
    text = safe_str(value).strip().replace("Z", "+00:00")
    if not text or text.lower() in NONE_VALUES:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _content_ref(value: Any) -> str:
    text = safe_str(value).strip()
    if not text or text.lower() in NONE_VALUES:
        return "none"
    if text.startswith("sha256:"):
        return text[:23]
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _one_line(value: Any, default: str = "none", *, limit: int = 160) -> str:
    text = compact_text(safe_str(value), limit).strip()
    return text if text else default


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build XinYu owner feedback effect state.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_owner_feedback_effect_report(args.root)
    if args.write:
        report.update(write_owner_feedback_effect(args.root, report, output=args.output))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_owner_feedback_effect_report(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
