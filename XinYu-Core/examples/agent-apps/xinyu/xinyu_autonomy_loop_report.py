from __future__ import annotations


__all__ = (
    "SHORT_TERM_CONTINUITY_STATE_REL",
    "SELF_THOUGHT_STATE_REL",
    "RELATION_STATE_REL",
    "INTENTION_STATE_REL",
    "ATTENTION_STATE_REL",
    "INTENTION_TRACE_REL",
    "REPORT_REL",
)

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from xinyu_live_loop_report import DEFAULT_CORE_URL
from xinyu_live_loop_report import build_report as build_live_loop_report
from xinyu_live_loop_report import _load_live_status
from xinyu_action_feedback_coverage import build_action_feedback_coverage_report
from xinyu_action_feedback_surface import read_action_feedback_state
from xinyu_owner_feedback_effects import build_owner_feedback_effect_report
from xinyu_perception_event_layer import build_perception_event_layer_report
from xinyu_perception_importance import build_perception_importance_report, perception_gap_signal
from xinyu_proactive_response_diagnostics import build_proactive_response_diagnostics
from xinyu_qq_reply_integrity_diagnostics import build_qq_reply_integrity_diagnostics
from xinyu_short_term_continuity_canary import build_short_term_continuity_canary_report
from xinyu_short_term_recall_diagnostics import build_short_term_recall_diagnostics
from xinyu_autonomy_loop_report_store import read_autonomy_loop_state_text
from xinyu_autonomy_loop_report_store import read_latest_intention_trace
from xinyu_autonomy_loop_report_store import write_autonomy_loop_report_text
from xinyu_autonomy_loop_report_store import ATTENTION_STATE_REL, INTENTION_STATE_REL, INTENTION_TRACE_REL, RELATION_STATE_REL, REPORT_REL, SELF_THOUGHT_STATE_REL, SHORT_TERM_CONTINUITY_STATE_REL




DEFAULT_WINDOW_MINUTES = 120

HOLD_OR_SILENCE_GATES = {"hold_or_silence", "hold_private", "silence", "blocked"}
HOLD_OR_SILENCE_ACTION_LEVELS = {"hold", "silence", "none"}
NONE_VALUES = {"", "missing", "unknown", "none"}


@dataclass(frozen=True)
class LoopCheck:
    name: str
    ok: bool
    detail: str
    stage: str
    required: bool = True


@dataclass(frozen=True)
class ActionEvidence:
    ok: bool
    detail: str
    surface: str
    signal: str
    result: str
    lifecycle: str
    future_effect: str


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _parse_md_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(_safe_str(value).strip())
    except (TypeError, ValueError):
        return default


def _check_by_name(report: dict[str, Any], name: str) -> dict[str, Any]:
    for check in report.get("checks", []):
        if isinstance(check, dict) and check.get("name") == name:
            return check
    return {"name": name, "ok": False, "detail": "missing_check"}


def _parse_timestamp(value: Any) -> datetime | None:
    text = _safe_str(value).strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _timestamp_not_before(left: Any, right: Any) -> bool:
    left_time = _parse_timestamp(left)
    right_time = _parse_timestamp(right)
    if left_time is None or right_time is None:
        return False
    compare_left = left_time
    compare_right = right_time
    if left_time.tzinfo is not None and right_time.tzinfo is not None:
        compare_right = right_time.astimezone(left_time.tzinfo)
    elif left_time.tzinfo is not None and right_time.tzinfo is None:
        compare_right = right_time.replace(tzinfo=left_time.tzinfo)
    elif left_time.tzinfo is None and right_time.tzinfo is not None:
        compare_left = left_time.replace(tzinfo=right_time.tzinfo)
    return compare_left >= compare_right


def _present(fields: dict[str, str], key: str, *, none_values: set[str] | None = None) -> bool:
    value = fields.get(key, "missing")
    blocked = {"", "missing", "unknown"}
    if none_values:
        blocked |= none_values
    return value not in blocked


def _surface_status(surfaces: dict[str, Any], name: str) -> str:
    surface = surfaces.get(name) if isinstance(surfaces.get(name), dict) else {}
    return _safe_str(surface.get("surface_status"), "missing")


def _surface_lifecycle(surfaces: dict[str, Any], name: str) -> str:
    surface = surfaces.get(name) if isinstance(surfaces.get(name), dict) else {}
    return _safe_str(surface.get("lifecycle_status"), "missing")


def _value_present(value: Any) -> bool:
    return _safe_str(value).strip().lower() not in NONE_VALUES


def _is_hold_or_silence_decision(intention: dict[str, str]) -> bool:
    gate = intention.get("selected_gate", "").strip()
    action_level = intention.get("action_level", "").strip()
    return gate in HOLD_OR_SILENCE_GATES or action_level in HOLD_OR_SILENCE_ACTION_LEVELS


def _has_specific_reason(value: Any) -> bool:
    return _safe_str(value).strip() not in NONE_VALUES


def _first_present(*values: Any) -> str:
    for value in values:
        text = _safe_str(value, "missing").strip()
        if text not in NONE_VALUES:
            return text
    return "missing"


def _audit_join(values: list[str]) -> str:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _safe_str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return ",".join(result[:8]) if result else "none"


def _audit_append(target: list[str], label: str, value: Any) -> None:
    text = _safe_str(value, "none").strip()
    if text.lower() not in NONE_VALUES:
        target.append(f"{label}:{text}")


def _feedback_consumption_audit_fields(
    intention: dict[str, str],
    *,
    action_feedback_signal: Any,
    action_feedback_future: Any,
    intention_action_feedback_bias: Any,
    intention_action_feedback_coverage_signal: Any,
    intention_action_feedback_coverage_lifecycle: Any,
    intention_action_feedback_coverage_bias: Any,
    action_feedback_coverage_future: Any,
    intention_owner_feedback_effect_signal: Any,
    intention_owner_feedback_effect_bias: Any,
    intention_owner_feedback_expression_bias: Any,
    owner_effect_future: Any,
    intention_owner_response_feedback_signal: Any,
    intention_owner_response_feedback_bias: Any,
    intention_owner_response_strategy_bias: Any,
    owner_response_future: Any,
    intention_perception_gap_signal: Any,
    intention_perception_gap_bias: Any,
    intention_perception_route_hint: Any,
) -> dict[str, str]:
    sources: list[str] = []
    biases: list[str] = []
    future_effects: list[str] = []

    if _value_present(action_feedback_signal):
        sources.append(f"action_feedback:{_safe_str(action_feedback_signal)}")
        _audit_append(biases, "action_feedback_bias", intention_action_feedback_bias)
        _audit_append(future_effects, "action_feedback_future", action_feedback_future)

    coverage_signal = _safe_str(intention_action_feedback_coverage_signal, "none")
    coverage_lifecycle = _safe_str(intention_action_feedback_coverage_lifecycle, "none")
    if _value_present(coverage_signal):
        source = f"action_feedback_coverage:{coverage_signal}"
        if _value_present(coverage_lifecycle):
            source = f"{source}/{coverage_lifecycle}"
        sources.append(source)
        _audit_append(biases, "action_feedback_coverage_bias", intention_action_feedback_coverage_bias)
        _audit_append(future_effects, "action_feedback_coverage_future", action_feedback_coverage_future)

    if _value_present(intention_owner_feedback_effect_signal):
        sources.append(f"owner_feedback_effect:{_safe_str(intention_owner_feedback_effect_signal)}")
        _audit_append(biases, "owner_feedback_effect_bias", intention_owner_feedback_effect_bias)
        _audit_append(biases, "owner_feedback_expression_bias", intention_owner_feedback_expression_bias)
        _audit_append(future_effects, "owner_feedback_future", owner_effect_future)

    if _value_present(intention_owner_response_feedback_signal):
        sources.append(f"owner_response_feedback:{_safe_str(intention_owner_response_feedback_signal)}")
        _audit_append(biases, "owner_response_feedback_bias", intention_owner_response_feedback_bias)
        _audit_append(biases, "owner_response_strategy_bias", intention_owner_response_strategy_bias)
        _audit_append(future_effects, "owner_response_future", owner_response_future)

    if _value_present(intention_perception_gap_signal):
        sources.append(f"perception_gap:{_safe_str(intention_perception_gap_signal)}")
        _audit_append(biases, "perception_gap_bias", intention_perception_gap_bias)
        _audit_append(future_effects, "perception_route_hint", intention_perception_route_hint)

    derived_status = "no_feedback"
    if sources and biases and future_effects:
        derived_status = "consumed"
    elif sources:
        derived_status = "partial"

    raw_status = _safe_str(intention.get("feedback_consumption_status"), "missing")
    raw_sources = _safe_str(intention.get("feedback_consumed_sources"), "missing")
    raw_biases = _safe_str(intention.get("feedback_consumed_biases"), "missing")
    raw_future = _safe_str(intention.get("feedback_consumed_future_effect"), "missing")

    return {
        "status": raw_status if _value_present(raw_status) else derived_status,
        "sources": raw_sources if _value_present(raw_sources) else _audit_join(sources),
        "biases": raw_biases if _value_present(raw_biases) else _audit_join(biases),
        "future_effect": raw_future if _value_present(raw_future) else _audit_join(future_effects),
    }


def _short_term_continuity_check(fields: dict[str, str]) -> LoopCheck:
    status = fields.get("status", "missing")
    direct_reference = fields.get("direct_reference", "missing")
    recall_status = fields.get("recall_status", "missing")
    recall_source = fields.get("recall_source", "missing")
    tail_count = fields.get("tail_count", "missing")
    archive_recovered_count = fields.get("archive_recovered_count", "missing")
    recent_user_count = fields.get("recent_user_count", "missing")
    recent_assistant_count = fields.get("recent_assistant_count", "missing")
    detail = (
        f"status={status}; direct_reference={direct_reference}; recall_status={recall_status}; "
        f"recall_source={recall_source}; tail_count={tail_count}; "
        f"archive_recovered_count={archive_recovered_count}; recent_user_count={recent_user_count}; "
        f"recent_assistant_count={recent_assistant_count}"
    )
    if direct_reference == "true":
        return LoopCheck(
            "short_term_continuity_anchor_visible",
            recall_status == "tail_available",
            detail,
            "input retention",
            required=True,
        )
    return LoopCheck(
        "short_term_continuity_anchor_visible",
        True,
        detail,
        "input retention",
        required=False,
    )


def _short_term_continuity_canary_check(report: dict[str, Any]) -> LoopCheck:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    status = _safe_str(report.get("status"), "missing")
    direct_reference_count = _as_int(metrics.get("direct_reference_count"), 0)
    detail = (
        f"status={status}; direct_reference_count={direct_reference_count}; "
        f"recall_success_rate={metrics.get('direct_reference_recall_success_rate_pct', 'missing')}; "
        f"matched_reply_count={metrics.get('matched_reply_count', 'missing')}; "
        f"unmatched_reply_count={metrics.get('unmatched_reply_count', 'missing')}; "
        f"which_sentence_recurrence_count={metrics.get('which_sentence_recurrence_count', 'missing')}"
    )
    if direct_reference_count <= 0:
        return LoopCheck(
            "short_term_continuity_canary",
            True,
            detail,
            "input retention",
            required=False,
        )
    return LoopCheck(
        "short_term_continuity_canary",
        status == "pass",
        detail,
        "input retention",
        required=True,
    )


def _short_term_recall_diagnostics_check(report: dict[str, Any]) -> LoopCheck:
    status = _safe_str(report.get("status"), "missing")
    direct_reference_count = _as_int(report.get("direct_reference_count"), 0)
    diagnostics = report.get("diagnostics") if isinstance(report.get("diagnostics"), dict) else {}
    detail = (
        f"status={status}; direct_reference_count={direct_reference_count}; "
        f"failure={report.get('primary_failure_class', 'missing')}; "
        f"tail={diagnostics.get('working_tail_status', 'missing')}; "
        f"archive={diagnostics.get('archive_fallback_status', 'missing')}; "
        f"prompt={diagnostics.get('prompt_admission_status', 'missing')}; "
        f"budget={diagnostics.get('prompt_budget_status', 'missing')}"
    )
    if direct_reference_count <= 0:
        return LoopCheck(
            "short_term_recall_diagnostics",
            True,
            detail,
            "input retention",
            required=False,
        )
    return LoopCheck(
        "short_term_recall_diagnostics",
        status == "pass",
        detail,
        "input retention",
        required=True,
    )


def _qq_reply_integrity_diagnostics_check(report: dict[str, Any]) -> LoopCheck:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    status = _safe_str(report.get("status"), "missing")
    visible_count = _as_int(metrics.get("visible_chat_reply_count"), 0)
    semantic_direct_count = _as_int(metrics.get("semantic_fast_direct_reply_count"), 0)
    detail = (
        f"status={status}; visible={visible_count}; "
        f"naked_ack={metrics.get('naked_ack_visible_reply_count', 'missing')}; "
        f"missing_working_memory={metrics.get('visible_reply_missing_working_memory_count', 'missing')}; "
        f"semantic_fast_direct={semantic_direct_count}; "
        f"semantic_fast_direct_without_archive="
        f"{metrics.get('semantic_fast_direct_reply_without_archive_count', 'missing')}; "
        f"semantic_fast_direct_without_visible_ack="
        f"{metrics.get('semantic_fast_direct_reply_without_visible_ack_count', 'missing')}"
    )
    if visible_count <= 0 and semantic_direct_count <= 0:
        return LoopCheck(
            "qq_reply_integrity_diagnostics",
            True,
            detail,
            "input retention",
            required=False,
        )
    return LoopCheck(
        "qq_reply_integrity_diagnostics",
        status == "pass",
        detail,
        "input retention",
        required=True,
    )


def _perception_event_layer_check(report: dict[str, Any]) -> LoopCheck:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    status = _safe_str(report.get("status"), "missing")
    event_count = _as_int(metrics.get("event_count"), 0)
    input_count = _as_int(metrics.get("input_event_count"), 0)
    source_count = _as_int(metrics.get("source_count"), 0)
    importance_count = _as_int(metrics.get("importance_ready_count"), 0)
    ok = status in {"pass", "partial"} and event_count > 0 and input_count > 0 and importance_count >= event_count
    return LoopCheck(
        "unified_perception_event_layer",
        ok,
        (
            f"status={status}; events={event_count}; sources={source_count}; "
            f"input={input_count}; qq={metrics.get('qq_event_count', 'missing')}; "
            f"desktop={metrics.get('desktop_event_count', 'missing')}; "
            f"tool={metrics.get('tool_result_event_count', 'missing')}; "
            f"system={metrics.get('system_health_event_count', 'missing')}; "
            f"file={metrics.get('file_change_event_count', 'missing')}; "
            f"anomaly={metrics.get('anomaly_count', 'missing')}"
        ),
        "unified perception event layer",
        required=True,
    )


def _perception_importance_check(report: dict[str, Any]) -> LoopCheck:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    status = _safe_str(report.get("status"), "missing")
    event_count = _as_int(metrics.get("event_count"), 0)
    judged_count = _as_int(metrics.get("judged_event_count"), 0)
    internal_gap_count = _as_int(metrics.get("internal_gap_count"), 0)
    ok = (
        status in {"pass", "partial"}
        and event_count > 0
        and judged_count >= event_count
        and internal_gap_count > 0
    )
    return LoopCheck(
        "perception_importance_judgment",
        ok,
        (
            f"status={status}; events={event_count}; judged={judged_count}; "
            f"high_attention={metrics.get('high_attention_count', 'missing')}; "
            f"anomaly={metrics.get('anomaly_judgment_count', 'missing')}; "
            f"gaps={internal_gap_count}; owner_attention={metrics.get('owner_attention_count', 'missing')}; "
            f"repair={metrics.get('repair_gap_count', 'missing')}; "
            f"maintenance={metrics.get('maintenance_gap_count', 'missing')}; "
            f"latest_gap={metrics.get('latest_gap_type', 'missing')}; "
            f"route={metrics.get('next_route_hint', 'missing')}"
        ),
        "importance/anomaly -> internal gap",
        required=True,
    )


def _perception_gap_consumed_check(
    report: dict[str, Any],
    intention: dict[str, str],
    attention: dict[str, str],
) -> LoopCheck:
    signal = perception_gap_signal(report)
    status = _safe_str(signal.get("status"), "missing")
    gap_type = _safe_str(signal.get("gap_type"), "none")
    route_hint = _safe_str(signal.get("route_hint"), "none")
    intention_gap = _safe_str(intention.get("perception_gap_signal"), "missing")
    intention_bias = _safe_str(intention.get("perception_gap_bias"), "missing")
    attention_gap = _safe_str(attention.get("perception_gap_type"), "missing")
    attention_consumed = _safe_str(attention.get("perception_gap_consumed"), "missing")
    required = status in {"pass", "partial"} and gap_type not in NONE_VALUES
    consumed = (
        intention_gap == gap_type
        and intention_bias not in NONE_VALUES
    ) or (
        attention_gap == gap_type
        and attention_consumed == "true"
    )
    return LoopCheck(
        "perception_gap_consumed_by_internal_state",
        (not required) or consumed,
        (
            f"status={status}; gap={gap_type}; route={route_hint}; "
            f"intention_gap={intention_gap}; intention_bias={intention_bias}; "
            f"attention_gap={attention_gap}; attention_consumed={attention_consumed}"
        ),
        "importance/anomaly -> internal state",
        required=required,
    )


def _candidate_competition_check(intention: dict[str, str]) -> LoopCheck:
    candidate_count = _as_int(intention.get("candidate_count"), 0)
    status = intention.get("candidate_competition_status", "missing")
    selected_score = intention.get("selected_total_score", "missing")
    runner_up = intention.get("runner_up_intent", "missing")
    runner_up_score = intention.get("runner_up_total_score", "missing")
    score_margin = intention.get("score_margin", "missing")
    blocked_count = intention.get("blocked_candidate_count", "missing")
    held_count = intention.get("held_candidate_count", "missing")
    review_gated_count = intention.get("review_gated_future_count", "missing")
    reason = intention.get("competition_reason", "missing")
    runner_up_reason = intention.get("runner_up_not_selected_reason", "missing")
    gate_pressure = intention.get("gate_pressure_summary", "missing")
    required = status not in NONE_VALUES
    ok = (
        not required
        or (
            status in {"observed", "observed_from_trace"}
            and selected_score not in NONE_VALUES
            and score_margin not in NONE_VALUES
            and reason not in NONE_VALUES
            and runner_up_reason not in NONE_VALUES
            and gate_pressure not in NONE_VALUES
            and (candidate_count <= 1 or runner_up not in NONE_VALUES)
        )
    )
    return LoopCheck(
        "candidate_competition_auditable",
        ok,
        (
            f"status={status}; candidates={candidate_count}; selected_score={selected_score}; "
            f"runner_up={runner_up}; runner_up_score={runner_up_score}; margin={score_margin}; "
            f"blocked={blocked_count}; held={held_count}; review_gated={review_gated_count}; "
            f"runner_up_reason={runner_up_reason}; gate_pressure={gate_pressure}; reason={reason}"
        ),
        "candidate intention/action",
        required=required,
    )


def _intention_with_trace_competition(root: Path, intention: dict[str, str]) -> dict[str, str]:
    if intention.get("candidate_competition_status", "missing") not in NONE_VALUES:
        return intention
    trace = _latest_intention_trace(root)
    candidates = trace.get("candidates") if isinstance(trace.get("candidates"), list) else []
    public_candidates = [item for item in candidates if isinstance(item, dict)]
    if not public_candidates:
        return intention
    selected = public_candidates[0]
    runner_up = public_candidates[1] if len(public_candidates) > 1 else {}
    selected_total = _as_int(selected.get("total_score"), 0)
    runner_total = _as_int(runner_up.get("total_score"), 0) if runner_up else 0
    selected_intent = _safe_str(selected.get("intent_type"), intention.get("selected_intent", "missing"))
    runner_intent = _safe_str(runner_up.get("intent_type"), "none") if runner_up else "none"
    runner_gate = _safe_str(runner_up.get("gate"), "none") if runner_up else "none"
    selected_value = _as_int(selected.get("value_score"), 0)
    selected_risk = _as_int(selected.get("risk_score"), 0)
    runner_value = _as_int(runner_up.get("value_score"), 0) if runner_up else 0
    runner_risk = _as_int(runner_up.get("risk_score"), 0) if runner_up else 0
    margin = selected_total - runner_total
    blocked = [item for item in public_candidates if item.get("gate") == "blocked"]
    held = [item for item in public_candidates if item.get("gate") in {"hold_or_silence", "hold_private", "silence"}]
    review_gated = [
        item
        for item in public_candidates
        if _safe_str(item.get("future_candidate"), "none") not in NONE_VALUES
    ]
    runner_reason = (
        "no_runner_up_to_compare"
        if not runner_up
        else (
            f"lower_total_score:margin={margin}; selected_value={selected_value}; "
            f"selected_risk={selected_risk}; runner_up_value={runner_value}; runner_up_risk={runner_risk}"
        )
    )
    gate_pressure = (
        f"selected_gate={_safe_str(selected.get('gate'), 'none')}; runner_up_gate={runner_gate}; "
        f"blocked={len(blocked)}; held={len(held)}; review_gated={len(review_gated)}"
    )
    reason = (
        f"selected={selected_intent}; runner_up={runner_intent}; "
        f"margin={margin}"
    )
    upgraded = dict(intention)
    upgraded.update(
        {
            "candidate_competition_status": "observed_from_trace",
            "selected_total_score": str(selected_total),
            "runner_up_intent": runner_intent,
            "runner_up_gate": runner_gate,
            "runner_up_total_score": str(runner_total),
            "score_margin": str(margin),
            "blocked_candidate_count": str(len(blocked)),
            "held_candidate_count": str(len(held)),
            "review_gated_future_count": str(len(review_gated)),
            "competition_reason": reason,
            "runner_up_not_selected_reason": runner_reason,
            "gate_pressure_summary": gate_pressure,
            "blocked_intents": _trace_intent_list(blocked),
            "held_intents": _trace_intent_list(held),
            "review_gated_intents": _trace_intent_list(review_gated),
        }
    )
    return upgraded


def _trace_intent_list(candidates: list[dict[str, Any]]) -> str:
    names = [_safe_str(item.get("intent_type"), "") for item in candidates[:6]]
    names = [name for name in names if name]
    return ",".join(names) if names else "none"


def _latest_intention_trace(root: Path) -> dict[str, Any]:
    return read_latest_intention_trace(root)


def _truthful_action_evidence(
    live_report: dict[str, Any],
    intention: dict[str, str],
    action_feedback_coverage: dict[str, Any],
) -> ActionEvidence:
    reply = _check_by_name(live_report, "visible_reply_sent")
    ack = _check_by_name(live_report, "qq_ack")
    stale = _check_by_name(live_report, "stale_reply_drop_guard")
    evidence = live_report.get("evidence") if isinstance(live_report.get("evidence"), dict) else {}
    private_input = evidence.get("latest_private_input") if isinstance(evidence.get("latest_private_input"), dict) else {}
    stale_drop = evidence.get("latest_stale_reply_drop") if isinstance(evidence.get("latest_stale_reply_drop"), dict) else {}
    gate = intention.get("selected_gate", "")
    action_level = intention.get("action_level", "")
    if bool(reply.get("ok")) and bool(ack.get("ok")):
        return ActionEvidence(
            True,
            "visible_reply_sent_and_qq_ack_observed",
            "qq",
            "qq_visible_reply_ack",
            "delivered",
            "acked",
            "confirm_visible_reply_transport_for_next_turn",
        )
    if bool(stale.get("ok")) and _timestamp_not_before(stale_drop.get("recorded_at"), private_input.get("recorded_at")):
        return ActionEvidence(
            True,
            "stale_reply_drop_observed; unsent replies must be retracted",
            "qq",
            "qq_stale_reply_drop",
            "unsent_retracted",
            "dropped",
            "prefer_latest_owner_input_and_suppress_stale_reply_memory",
        )
    if gate in HOLD_OR_SILENCE_GATES or action_level in HOLD_OR_SILENCE_ACTION_LEVELS:
        result = gate or action_level
        return ActionEvidence(
            True,
            f"bounded_non_action:{result}",
            "none",
            "bounded_non_action",
            result,
            "held",
            "no_outward_action_taken",
        )
    local = _local_action_evidence(intention, action_feedback_coverage)
    if local is not None:
        return local
    if bool(stale.get("ok")):
        return ActionEvidence(
            False,
            "stale_reply_drop_is_older_than_latest_private_input",
            "qq",
            "qq_stale_reply_drop",
            "stale_drop_older_than_latest_input",
            "needs_check",
            "prefer_latest_owner_input_before_claiming_drop",
        )
    return ActionEvidence(
        False,
        "no verified action result, stale drop, explicit silence gate, or local action evidence",
        "missing",
        "missing",
        "missing",
        "missing",
        "missing",
    )


def _local_action_evidence(
    intention: dict[str, str],
    action_feedback_coverage: dict[str, Any],
) -> ActionEvidence | None:
    if not _local_action_evidence_allowed(intention):
        return None
    selected = _select_local_action_surface(action_feedback_coverage)
    if selected is None:
        return None
    surface_name, surface = selected
    status = _safe_str(surface.get("surface_status"), "missing")
    signal = _safe_str(surface.get("feedback_signal"), "missing")
    result = _safe_str(surface.get("action_result"), "missing")
    lifecycle = _safe_str(surface.get("lifecycle_status"), "missing")
    future_effect = _safe_str(surface.get("future_effect"), "missing")
    if status == "needs_check":
        prefix = "local_action_result_needs_check"
    elif status == "partial":
        prefix = "local_action_result_partial"
    else:
        prefix = "local_action_result_observed"
    return ActionEvidence(
        True,
        f"{prefix}:{surface_name}/{signal}/{result}",
        surface_name,
        signal,
        result,
        lifecycle,
        future_effect,
    )


def _local_action_evidence_allowed(intention: dict[str, str]) -> bool:
    intent = _safe_str(intention.get("selected_intent")).strip()
    action_level = _safe_str(intention.get("action_level")).strip().lower()
    if intent == "do_bounded_task":
        return True
    return any(marker in action_level for marker in ("local", "tool", "codex", "patch", "probe"))


def _select_local_action_surface(report: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    surfaces = report.get("surfaces") if isinstance(report.get("surfaces"), dict) else {}
    candidates: list[tuple[str, dict[str, Any]]] = []
    for name, surface in surfaces.items():
        if name == "qq" or not isinstance(surface, dict):
            continue
        if surface.get("observed") is not True:
            continue
        if not _value_present(surface.get("feedback_signal")) or not _value_present(surface.get("action_result")):
            continue
        candidates.append((str(name), surface))
    if not candidates:
        return None

    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    latest_name = _safe_str(metrics.get("latest_feedback_surface"), "").strip()
    if latest_name and latest_name != "qq":
        for name, surface in candidates:
            if name == latest_name:
                return name, surface

    dated: list[tuple[datetime, str, dict[str, Any]]] = []
    for name, surface in candidates:
        parsed = _parse_timestamp(surface.get("checked_at"))
        if parsed is not None:
            dated.append((parsed, name, surface))
    if dated:
        dated.sort(key=lambda item: item[0])
        _, name, surface = dated[-1]
        return name, surface
    return candidates[-1]


def build_autonomy_loop_report(
    root: Path,
    *,
    status_data: dict[str, Any] | None = None,
    status_error: str = "",
    now: datetime | None = None,
    window_minutes: int = DEFAULT_WINDOW_MINUTES,
) -> dict[str, Any]:
    root = root.resolve()
    now = now or datetime.now(timezone.utc)
    live_report = build_live_loop_report(
        root,
        status_data=status_data,
        status_error=status_error,
        now=now,
        window_minutes=max(1, int(window_minutes)),
    )
    intention = _intention_with_trace_competition(
        root,
        _parse_md_fields(read_autonomy_loop_state_text(root, INTENTION_STATE_REL)),
    )
    attention = _parse_md_fields(read_autonomy_loop_state_text(root, ATTENTION_STATE_REL))
    relation = _parse_md_fields(read_autonomy_loop_state_text(root, RELATION_STATE_REL))
    self_thought = _parse_md_fields(read_autonomy_loop_state_text(root, SELF_THOUGHT_STATE_REL))
    short_term_continuity = _parse_md_fields(read_autonomy_loop_state_text(root, SHORT_TERM_CONTINUITY_STATE_REL))
    short_term_continuity_canary = build_short_term_continuity_canary_report(
        root,
        lookback_minutes=max(1, int(window_minutes)),
        generated_at=now.isoformat(),
    )
    short_term_recall_diagnostics = build_short_term_recall_diagnostics(root)
    qq_reply_integrity = build_qq_reply_integrity_diagnostics(
        root,
        lookback_minutes=max(1, int(window_minutes)),
        generated_at=now.isoformat(),
    )
    action_feedback = read_action_feedback_state(root)
    action_feedback_coverage = build_action_feedback_coverage_report(root, generated_at=now.isoformat())
    perception_event_layer = build_perception_event_layer_report(
        root,
        generated_at=now.isoformat(),
        action_feedback_coverage=action_feedback_coverage,
    )
    perception_importance = build_perception_importance_report(
        root,
        generated_at=now.isoformat(),
        perception_event_layer=perception_event_layer,
    )
    perception_signal = perception_gap_signal(perception_importance)
    owner_feedback_effect = build_owner_feedback_effect_report(root, generated_at=now.isoformat())
    proactive_response_diagnostics = build_proactive_response_diagnostics(root, generated_at=now.isoformat())
    coverage_metrics = (
        action_feedback_coverage.get("metrics")
        if isinstance(action_feedback_coverage.get("metrics"), dict)
        else {}
    )
    coverage_surfaces = (
        action_feedback_coverage.get("surfaces")
        if isinstance(action_feedback_coverage.get("surfaces"), dict)
        else {}
    )

    runtime_ok = bool(_check_by_name(live_report, "runtime_status").get("ok"))
    input_ok = bool(_check_by_name(live_report, "private_input").get("ok"))
    dispatch_ok = bool(_check_by_name(live_report, "dispatch_started").get("ok"))
    shadow_ok = bool(_check_by_name(live_report, "visible_send_shadow_guard").get("ok"))
    action_evidence = _truthful_action_evidence(live_report, intention, action_feedback_coverage)
    action_ok = action_evidence.ok
    action_detail = action_evidence.detail
    hold_or_silence_required = _is_hold_or_silence_decision(intention)

    selected_intent = intention.get("selected_intent", "missing")
    selected_gate = intention.get("selected_gate", "missing")
    action_level = intention.get("action_level", "missing")
    candidate_count = _as_int(intention.get("candidate_count"), 0)
    proactive_candidate = intention.get("proactive_candidate", "missing")
    memory_candidate = intention.get("memory_candidate", "missing")
    feedback_signal = intention.get("feedback_signal", "missing")
    intention_action_feedback_signal = intention.get("action_feedback_signal", "missing")
    intention_action_feedback_bias = intention.get("action_feedback_bias", "missing")
    intention_action_feedback_coverage_signal = intention.get("action_feedback_coverage_signal", "missing")
    intention_action_feedback_coverage_lifecycle = intention.get("action_feedback_coverage_lifecycle", "missing")
    intention_action_feedback_coverage_bias = intention.get("action_feedback_coverage_bias", "missing")
    intention_owner_feedback_effect_signal = intention.get("owner_feedback_effect_signal", "missing")
    intention_owner_feedback_effect_bias = intention.get("owner_feedback_effect_bias", "missing")
    intention_owner_feedback_expression_bias = intention.get("owner_feedback_expression_bias", "missing")
    intention_owner_response_feedback_signal = intention.get("owner_response_feedback_signal", "missing")
    intention_owner_response_feedback_bias = intention.get("owner_response_feedback_bias", "missing")
    intention_owner_response_strategy_bias = intention.get("owner_response_strategy_bias", "missing")
    intention_perception_gap_signal = intention.get("perception_gap_signal", "missing")
    intention_perception_gap_bias = intention.get("perception_gap_bias", "missing")
    intention_perception_route_hint = intention.get("perception_route_hint", "missing")
    candidate_competition_status = intention.get("candidate_competition_status", "missing")
    selected_total_score = intention.get("selected_total_score", "missing")
    runner_up_intent = intention.get("runner_up_intent", "missing")
    runner_up_gate = intention.get("runner_up_gate", "missing")
    runner_up_total_score = intention.get("runner_up_total_score", "missing")
    score_margin = intention.get("score_margin", "missing")
    blocked_candidate_count = intention.get("blocked_candidate_count", "missing")
    held_candidate_count = intention.get("held_candidate_count", "missing")
    review_gated_future_count = intention.get("review_gated_future_count", "missing")
    competition_reason = intention.get("competition_reason", "missing")
    runner_up_not_selected_reason = intention.get("runner_up_not_selected_reason", "missing")
    gate_pressure_summary = intention.get("gate_pressure_summary", "missing")
    blocked_intents = intention.get("blocked_intents", "missing")
    held_intents = intention.get("held_intents", "missing")
    review_gated_intents = intention.get("review_gated_intents", "missing")
    restraint_reason = intention.get("restraint_reason", "missing")
    raw_private_body_retained = intention.get("raw_private_body_retained", "missing")
    stable_memory_write = intention.get("stable_memory_write", "missing")

    candidate_ok = candidate_count > 0 or selected_intent not in {"", "missing", "unknown", "none"}
    gate_ok = selected_gate not in {"", "missing", "unknown"} and action_level not in {"", "missing", "unknown"}
    hold_or_silence_ok = (not hold_or_silence_required) or _has_specific_reason(restraint_reason)
    boundary_ok = raw_private_body_retained in {"false", "missing"} and stable_memory_write in {
        "gated",
        "blocked",
        "missing",
    }
    action_feedback_signal = action_feedback.get("feedback_signal", "missing")
    action_feedback_result = action_feedback.get("action_result", "missing")
    action_feedback_future = action_feedback.get("future_effect", "missing")
    action_feedback_memory = action_feedback.get("memory_effect", "missing")
    coverage_status = _safe_str(action_feedback_coverage.get("status"), "missing")
    coverage_observed_count = _as_int(coverage_metrics.get("observed_surface_count"), 0)
    coverage_non_qq_count = _as_int(coverage_metrics.get("non_qq_surface_count"), 0)
    coverage_future_effect_count = _as_int(coverage_metrics.get("future_effect_count"), 0)
    coverage_failure_count = _as_int(coverage_metrics.get("failure_count"), 0)
    if _safe_str(intention_action_feedback_coverage_lifecycle, "missing") in NONE_VALUES:
        coverage_latest_signal = _safe_str(coverage_metrics.get("latest_feedback_signal"), "missing")
        if action_evidence.signal == intention_action_feedback_coverage_signal:
            intention_action_feedback_coverage_lifecycle = action_evidence.lifecycle
        elif coverage_latest_signal == intention_action_feedback_coverage_signal:
            intention_action_feedback_coverage_lifecycle = _safe_str(
                coverage_metrics.get("latest_lifecycle_status"),
                "missing",
            )
    coverage_selected_surface = _select_local_action_surface(action_feedback_coverage)
    action_feedback_coverage_future = "none"
    if coverage_selected_surface is not None:
        selected_signal = _safe_str(coverage_selected_surface[1].get("feedback_signal"), "missing")
        if selected_signal == intention_action_feedback_coverage_signal:
            action_feedback_coverage_future = _safe_str(coverage_selected_surface[1].get("future_effect"), "none")
    if action_feedback_coverage_future in NONE_VALUES and action_evidence.signal == intention_action_feedback_coverage_signal:
        action_feedback_coverage_future = action_evidence.future_effect
    coverage_required = coverage_non_qq_count > 0
    coverage_ok = (
        not coverage_required
        or (
            coverage_status in {"pass", "partial"}
            and coverage_failure_count == 0
            and coverage_future_effect_count >= coverage_non_qq_count
        )
    )
    coverage_consumed_ok = (
        not coverage_required
        or (
            intention_action_feedback_coverage_signal not in {"", "missing", "unknown", "none"}
            and intention_action_feedback_coverage_bias not in {"", "missing", "unknown", "none"}
        )
    )
    direct_feedback_ok = (
        action_feedback_signal not in {"", "missing", "unknown", "none"}
        and action_feedback_result not in {"", "missing", "unknown", "none"}
        and action_feedback_future not in {"", "missing", "unknown", "none"}
        and intention_action_feedback_signal == action_feedback_signal
        and intention_action_feedback_bias not in {"", "missing", "unknown", "none"}
    )
    coverage_feedback_ok = coverage_required and coverage_ok and coverage_consumed_ok
    feedback_ok = direct_feedback_ok or coverage_feedback_ok
    visible_send_guard_required = (
        (not hold_or_silence_required)
        and action_level.startswith("visible")
        and action_evidence.surface in {"qq", "missing"}
    )
    feedback_required = not hold_or_silence_required
    owner_effect_status = _safe_str(owner_feedback_effect.get("status"), "missing")
    owner_effect_signal = _safe_str(owner_feedback_effect.get("latest_feedback_kind"), "none")
    owner_effect_bias = _safe_str(owner_feedback_effect.get("intention_bias"), "none")
    owner_effect_expression = _safe_str(owner_feedback_effect.get("expression_strategy_bias"), "none")
    owner_effect_future = _safe_str(owner_feedback_effect.get("future_effect"), "none")
    owner_effect_realtime_pressure = _safe_str(owner_feedback_effect.get("realtime_pressure_status"), "normal")
    intention_notes = _safe_str(intention.get("notes"), "none")
    owner_effect_required = owner_effect_status in {"active", "supported"}
    owner_effect_cooldown_ok = (
        owner_effect_status == "active"
        and owner_effect_signal == "owner_reported_template_voice_failure"
        and owner_effect_realtime_pressure == "capped_direct_failure_only"
        and owner_effect_future == "style_repair_direct_only_ordinary_chat_keeps_current_anchor"
        and intention_owner_feedback_effect_signal in {"", "missing", "unknown", "none"}
        and intention_owner_feedback_effect_bias in {"", "missing", "unknown", "none"}
        and intention_owner_feedback_expression_bias in {"", "missing", "unknown", "none"}
        and "owner_feedback_effect_cooldown:direct_failure_only" in intention_notes
    )
    owner_effect_consumed_ok = (
        not owner_effect_required
        or owner_effect_cooldown_ok
        or (
            intention_owner_feedback_effect_signal == owner_effect_signal
            and intention_owner_feedback_effect_bias not in {"", "missing", "unknown", "none"}
            and intention_owner_feedback_expression_bias not in {"", "missing", "unknown", "none"}
            and owner_effect_bias not in {"", "missing", "unknown", "none"}
            and owner_effect_expression not in {"", "missing", "unknown", "none"}
            and owner_effect_future not in {"", "missing", "unknown", "none"}
        )
    )
    owner_response_signal = _safe_str(owner_feedback_effect.get("owner_response_signal"), "none")
    owner_response_bias = _safe_str(owner_feedback_effect.get("owner_response_intention_bias"), "none")
    owner_response_strategy = _safe_str(owner_feedback_effect.get("owner_response_strategy_bias"), "none")
    owner_response_future = _safe_str(owner_feedback_effect.get("owner_response_future_effect"), "none")
    owner_response_required = owner_response_signal not in {"", "missing", "unknown", "none"}
    owner_response_consumed_ok = (
        not owner_response_required
        or (
            intention_owner_response_feedback_signal == owner_response_signal
            and intention_owner_response_feedback_bias not in {"", "missing", "unknown", "none"}
            and intention_owner_response_strategy_bias not in {"", "missing", "unknown", "none"}
            and owner_response_bias not in {"", "missing", "unknown", "none"}
            and owner_response_strategy not in {"", "missing", "unknown", "none"}
            and owner_response_future not in {"", "missing", "unknown", "none"}
        )
    )
    feedback_consumption = _feedback_consumption_audit_fields(
        intention,
        action_feedback_signal=action_feedback_signal,
        action_feedback_future=action_feedback_future,
        intention_action_feedback_bias=intention_action_feedback_bias,
        intention_action_feedback_coverage_signal=intention_action_feedback_coverage_signal,
        intention_action_feedback_coverage_lifecycle=intention_action_feedback_coverage_lifecycle,
        intention_action_feedback_coverage_bias=intention_action_feedback_coverage_bias,
        action_feedback_coverage_future=action_feedback_coverage_future,
        intention_owner_feedback_effect_signal=intention_owner_feedback_effect_signal,
        intention_owner_feedback_effect_bias=intention_owner_feedback_effect_bias,
        intention_owner_feedback_expression_bias=intention_owner_feedback_expression_bias,
        owner_effect_future=owner_effect_future,
        intention_owner_response_feedback_signal=intention_owner_response_feedback_signal,
        intention_owner_response_feedback_bias=intention_owner_response_feedback_bias,
        intention_owner_response_strategy_bias=intention_owner_response_strategy_bias,
        owner_response_future=owner_response_future,
        intention_perception_gap_signal=intention_perception_gap_signal,
        intention_perception_gap_bias=intention_perception_gap_bias,
        intention_perception_route_hint=intention_perception_route_hint,
    )
    feedback_consumption_status = feedback_consumption["status"]
    feedback_consumed_sources = feedback_consumption["sources"]
    feedback_consumed_biases = feedback_consumption["biases"]
    feedback_consumed_future_effect = feedback_consumption["future_effect"]
    feedback_consumption_required = feedback_consumed_sources not in NONE_VALUES
    feedback_consumption_auditable_ok = (
        not feedback_consumption_required
        or (
            feedback_consumption_status == "consumed"
            and feedback_consumed_biases not in NONE_VALUES
            and feedback_consumed_future_effect not in NONE_VALUES
        )
    )
    proactive_response_status = _safe_str(proactive_response_diagnostics.get("status"), "missing")
    proactive_response_signal = _safe_str(proactive_response_diagnostics.get("response_signal_candidate"), "none")
    proactive_response_required = proactive_response_status in {
        "waiting",
        "timeout_active",
        "delivery_failed",
        "response_recorded",
    }
    proactive_response_diagnostic_ok = (
        not proactive_response_required
        or proactive_response_signal not in {"", "missing", "unknown", "none"}
    )

    checks = [
        LoopCheck(
            "runtime_alive",
            runtime_ok,
            _safe_str(_check_by_name(live_report, "runtime_status").get("detail")),
            "external/internal input surface",
        ),
        LoopCheck(
            "input_anchor_observed",
            input_ok,
            _safe_str(_check_by_name(live_report, "private_input").get("detail")),
            "input retention",
        ),
        _short_term_continuity_check(short_term_continuity),
        _short_term_continuity_canary_check(short_term_continuity_canary),
        _short_term_recall_diagnostics_check(short_term_recall_diagnostics),
        _qq_reply_integrity_diagnostics_check(qq_reply_integrity),
        _perception_event_layer_check(perception_event_layer),
        _perception_importance_check(perception_importance),
        _perception_gap_consumed_check(perception_importance, intention, attention),
        LoopCheck(
            "dispatch_reached_core",
            dispatch_ok,
            _safe_str(_check_by_name(live_report, "dispatch_started").get("detail")),
            "input -> thought boundary",
        ),
        LoopCheck(
            "internal_state_gap_visible",
            _present(intention, "selected_intent")
            or _present(attention, "attention_mode")
            or _as_int(perception_importance.get("metrics", {}).get("internal_gap_count"), 0) > 0,
            (
                f"selected_intent={selected_intent}; "
                f"attention_mode={attention.get('attention_mode', 'missing')}; "
                f"perception_gap={perception_importance.get('metrics', {}).get('latest_gap_type', 'missing')}; "
                f"perception_gap_count={perception_importance.get('metrics', {}).get('internal_gap_count', 'missing')}"
            ),
            "internal state / need",
        ),
        LoopCheck(
            "candidate_generated",
            candidate_ok,
            f"candidate_count={candidate_count}; selected_intent={selected_intent}",
            "candidate intention/action",
        ),
        _candidate_competition_check(intention),
        LoopCheck(
            "gate_decision_visible",
            gate_ok,
            f"selected_gate={selected_gate}; action_level={action_level}",
            "gate / boundary",
        ),
        LoopCheck(
            "silence_or_hold_explained",
            hold_or_silence_ok,
            (
                f"selected_gate={selected_gate}; action_level={action_level}; "
                f"restraint_reason={restraint_reason}; proactive_candidate={proactive_candidate}; "
                f"memory_candidate={memory_candidate}"
            ),
            "gate / boundary",
            required=hold_or_silence_required,
        ),
        LoopCheck(
            "truthful_action_result",
            action_ok,
            action_detail,
            "bounded action result",
        ),
        LoopCheck(
            "visible_send_privacy_guard",
            (not visible_send_guard_required) or shadow_ok,
            (
                _safe_str(_check_by_name(live_report, "visible_send_shadow_guard").get("detail"))
                if visible_send_guard_required
                else f"not_required_for_gate={selected_gate}/action_level={action_level}"
            ),
            "action privacy boundary",
            required=visible_send_guard_required,
        ),
        LoopCheck(
            "feedback_changes_future_surface",
            (not feedback_required) or feedback_ok,
            (
                f"feedback_signal={action_feedback_signal}; action_result={action_feedback_result}; "
                f"future_effect={action_feedback_future}; memory_effect={action_feedback_memory}; "
                f"intention_feedback_signal={intention_action_feedback_signal}; "
                f"intention_feedback_bias={intention_action_feedback_bias}; "
                f"coverage_feedback={str(coverage_feedback_ok).lower()}; "
                f"coverage_signal={intention_action_feedback_coverage_signal}; "
                f"coverage_lifecycle={intention_action_feedback_coverage_lifecycle}; "
                f"coverage_bias={intention_action_feedback_coverage_bias}"
            ),
            "feedback -> future behavior",
            required=feedback_required,
        ),
        LoopCheck(
            "multi_action_feedback_coverage",
            coverage_ok,
            (
                f"status={coverage_status}; observed={coverage_observed_count}; "
                f"non_qq={coverage_non_qq_count}; future_effects={coverage_future_effect_count}; "
                f"failures={coverage_failure_count}; "
                f"latest={coverage_metrics.get('latest_feedback_surface', 'none')}/"
                f"{coverage_metrics.get('latest_feedback_signal', 'none')}"
            ),
            "feedback -> future behavior",
            required=coverage_required,
        ),
        LoopCheck(
            "multi_action_feedback_consumed_by_intention",
            coverage_consumed_ok,
            (
                f"coverage_signal={intention_action_feedback_coverage_signal}; "
                f"coverage_lifecycle={intention_action_feedback_coverage_lifecycle}; "
                f"coverage_bias={intention_action_feedback_coverage_bias}; "
                f"non_qq={coverage_non_qq_count}; latest={coverage_metrics.get('latest_feedback_surface', 'none')}/"
                f"{coverage_metrics.get('latest_feedback_signal', 'none')}"
            ),
            "feedback -> future behavior",
            required=coverage_required,
        ),
        LoopCheck(
            "owner_feedback_changes_expression_strategy",
            owner_effect_consumed_ok,
            (
                f"status={owner_effect_status}; signal={owner_effect_signal}; "
                f"expression_bias={owner_effect_expression}; intention_bias={owner_effect_bias}; "
                f"future_effect={owner_effect_future}; realtime_pressure={owner_effect_realtime_pressure}; "
                f"intention_signal={intention_owner_feedback_effect_signal}; "
                f"intention_bias={intention_owner_feedback_effect_bias}; "
                f"intention_expression_bias={intention_owner_feedback_expression_bias}"
            ),
            "feedback -> future behavior",
            required=owner_effect_required,
        ),
        LoopCheck(
            "owner_response_changes_request_strategy",
            owner_response_consumed_ok,
            (
                f"signal={owner_response_signal}; strategy_bias={owner_response_strategy}; "
                f"intention_bias={owner_response_bias}; future_effect={owner_response_future}; "
                f"intention_signal={intention_owner_response_feedback_signal}; "
                f"intention_bias={intention_owner_response_feedback_bias}; "
                f"intention_strategy_bias={intention_owner_response_strategy_bias}"
            ),
            "feedback -> future behavior",
            required=owner_response_required,
        ),
        LoopCheck(
            "feedback_consumption_auditable",
            feedback_consumption_auditable_ok,
            (
                f"status={feedback_consumption_status}; sources={feedback_consumed_sources}; "
                f"biases={feedback_consumed_biases}; future={feedback_consumed_future_effect}"
            ),
            "feedback -> future behavior",
            required=feedback_consumption_required,
        ),
        LoopCheck(
            "proactive_response_feedback_diagnostic",
            proactive_response_diagnostic_ok,
            (
                f"status={proactive_response_status}; signal={proactive_response_signal}; "
                f"waiting={proactive_response_diagnostics.get('delivered_waiting_owner', False)}; "
                f"timeout={proactive_response_diagnostics.get('timeout_active', False)}; "
                f"age_minutes={proactive_response_diagnostics.get('age_minutes', 'unknown')}; "
                f"minutes_until_timeout="
                f"{proactive_response_diagnostics.get('minutes_until_no_response_timeout', 'none')}"
            ),
            "feedback -> future behavior",
            required=proactive_response_required,
        ),
        LoopCheck(
            "memory_boundary_held",
            boundary_ok,
            f"stable_memory_write={stable_memory_write}; raw_private_body_retained={raw_private_body_retained}",
            "memory boundary",
        ),
    ]

    required_ok = all(check.ok for check in checks if check.required)
    decision_chain = {
        "input_anchor": "observed" if input_ok else "missing",
        "perception_gap": perception_signal.get("gap_type", "missing"),
        "perception_route_hint": perception_signal.get("route_hint", "missing"),
        "perception_internal_consumed": (
            "true"
            if any(
                check.name == "perception_gap_consumed_by_internal_state" and check.ok
                for check in checks
            )
            else "false"
        ),
        "internal_state": selected_intent,
        "candidate_count": candidate_count,
        "selected_candidate": selected_intent,
        "selected_total_score": selected_total_score,
        "runner_up_intent": runner_up_intent,
        "runner_up_gate": runner_up_gate,
        "runner_up_total_score": runner_up_total_score,
        "score_margin": score_margin,
        "blocked_candidate_count": blocked_candidate_count,
        "held_candidate_count": held_candidate_count,
        "review_gated_future_count": review_gated_future_count,
        "competition_reason": competition_reason,
        "runner_up_not_selected_reason": runner_up_not_selected_reason,
        "gate_pressure_summary": gate_pressure_summary,
        "blocked_intents": blocked_intents,
        "held_intents": held_intents,
        "review_gated_intents": review_gated_intents,
        "gate": selected_gate,
        "action_level": action_level,
        "action_result": action_detail if action_ok else "unverified",
        "action_evidence_surface": action_evidence.surface,
        "action_evidence_signal": action_evidence.signal,
        "action_evidence_result": action_evidence.result,
        "action_evidence_lifecycle": action_evidence.lifecycle,
        "action_evidence_future_effect": action_evidence.future_effect,
        "restraint_reason": restraint_reason,
        "proactive_candidate": proactive_candidate,
        "memory_candidate": memory_candidate,
        "action_feedback_signal": action_feedback_signal,
        "action_feedback_future_effect": action_feedback_future,
        "owner_feedback_signal": owner_effect_signal,
        "owner_feedback_future_effect": owner_effect_future,
        "owner_response_signal": owner_response_signal,
        "owner_response_future_effect": owner_response_future,
        "feedback_consumption_status": feedback_consumption_status,
        "feedback_consumed_sources": feedback_consumed_sources,
        "feedback_consumed_biases": feedback_consumed_biases,
        "feedback_consumed_future_effect": feedback_consumed_future_effect,
        "proactive_response_signal": proactive_response_signal,
        "proactive_response_future_effect": proactive_response_diagnostics.get(
            "future_effect_if_timeout",
            "missing",
        ),
        "next_behavior_bias": _safe_str(
            _first_present(
                intention_owner_feedback_effect_bias,
                intention_owner_response_feedback_bias,
                intention_action_feedback_coverage_bias,
                intention_action_feedback_bias,
                intention_perception_gap_bias,
            ),
            "missing",
        ),
    }
    return {
        "ok": required_ok,
        "generated_at": now.isoformat(),
        "root": str(root),
        "window_minutes": max(1, int(window_minutes)),
        "definition": "bounded_verifiable_self_generating_autonomy_loop",
        "checks": [check.__dict__ for check in checks],
        "live_loop": {
            "ok": bool(live_report.get("ok")),
            "checks": live_report.get("checks", []),
            "evidence": live_report.get("evidence", {}),
        },
        "state": {
            "decision_chain": decision_chain,
            "intention": {
                "selected_intent": selected_intent,
                "selected_gate": selected_gate,
                "action_level": action_level,
                "autonomy_posture": intention.get("autonomy_posture", "missing"),
                "feedback_signal": feedback_signal,
                "action_feedback_signal": intention_action_feedback_signal,
                "action_feedback_bias": intention_action_feedback_bias,
                "action_feedback_coverage_signal": intention_action_feedback_coverage_signal,
                "action_feedback_coverage_lifecycle": intention_action_feedback_coverage_lifecycle,
                "action_feedback_coverage_bias": intention_action_feedback_coverage_bias,
                "owner_feedback_effect_signal": intention_owner_feedback_effect_signal,
                "owner_feedback_effect_bias": intention_owner_feedback_effect_bias,
                "owner_feedback_expression_bias": intention_owner_feedback_expression_bias,
                "owner_response_feedback_signal": intention_owner_response_feedback_signal,
                "owner_response_feedback_bias": intention_owner_response_feedback_bias,
                "owner_response_strategy_bias": intention_owner_response_strategy_bias,
                "perception_gap_signal": intention_perception_gap_signal,
                "perception_gap_bias": intention_perception_gap_bias,
                "perception_route_hint": intention_perception_route_hint,
                "feedback_consumption_status": feedback_consumption_status,
                "feedback_consumed_sources": feedback_consumed_sources,
                "feedback_consumed_biases": feedback_consumed_biases,
                "feedback_consumed_future_effect": feedback_consumed_future_effect,
                "candidate_competition_status": candidate_competition_status,
                "selected_total_score": selected_total_score,
                "runner_up_intent": runner_up_intent,
                "runner_up_gate": runner_up_gate,
                "runner_up_total_score": runner_up_total_score,
                "score_margin": score_margin,
                "blocked_candidate_count": blocked_candidate_count,
                "held_candidate_count": held_candidate_count,
                "review_gated_future_count": review_gated_future_count,
                "competition_reason": competition_reason,
                "runner_up_not_selected_reason": runner_up_not_selected_reason,
                "gate_pressure_summary": gate_pressure_summary,
                "blocked_intents": blocked_intents,
                "held_intents": held_intents,
                "review_gated_intents": review_gated_intents,
                "proactive_candidate": proactive_candidate,
                "memory_candidate": memory_candidate,
                "restraint_reason": restraint_reason,
                "proactive_delivery": intention.get("proactive_delivery", "missing"),
                "stable_memory_write": stable_memory_write,
                "raw_private_body_retained": raw_private_body_retained,
            },
            "attention": {
                "attention_mode": attention.get("attention_mode", "missing"),
                "attention_target": attention.get("attention_target", "missing"),
                "last_route": attention.get("last_route", "missing"),
                "ignored_event_count": attention.get("ignored_event_count", "missing"),
                "noted_event_count": attention.get("noted_event_count", "missing"),
                "perception_gap_type": attention.get("perception_gap_type", "missing"),
                "perception_route_hint": attention.get("perception_route_hint", "missing"),
                "perception_gap_bias": attention.get("perception_gap_bias", "missing"),
                "perception_gap_consumed": attention.get("perception_gap_consumed", "missing"),
            },
            "relation": {
                "scene": relation.get("scene", "missing"),
                "user_need": relation.get("user_need", "missing"),
                "response_posture": relation.get("response_posture", "missing"),
                "initiative_allowed": relation.get("initiative_allowed", "missing"),
            },
            "self_thought": {
                "candidate_enabled": self_thought.get("candidate_enabled", "missing"),
                "status": self_thought.get("status", "missing"),
                "route": self_thought.get("route", "missing"),
            },
            "short_term_continuity": {
                "status": short_term_continuity.get("status", "missing"),
                "direct_reference": short_term_continuity.get("direct_reference", "missing"),
                "recall_status": short_term_continuity.get("recall_status", "missing"),
                "recall_source": short_term_continuity.get("recall_source", "missing"),
                "tail_count": short_term_continuity.get("tail_count", "missing"),
                "archive_recovered_count": short_term_continuity.get("archive_recovered_count", "missing"),
                "recent_user_count": short_term_continuity.get("recent_user_count", "missing"),
                "recent_assistant_count": short_term_continuity.get("recent_assistant_count", "missing"),
                "latest_user_ref": short_term_continuity.get("latest_user_ref", "missing"),
                "latest_assistant_ref": short_term_continuity.get("latest_assistant_ref", "missing"),
            },
            "short_term_continuity_canary": {
                "status": short_term_continuity_canary.get("status", "missing"),
                "direct_reference_count": short_term_continuity_canary.get("metrics", {}).get(
                    "direct_reference_count",
                    "missing",
                ),
                "recall_success_rate": short_term_continuity_canary.get("metrics", {}).get(
                    "direct_reference_recall_success_rate_pct",
                    "missing",
                ),
                "matched_reply_count": short_term_continuity_canary.get("metrics", {}).get(
                    "matched_reply_count",
                    "missing",
                ),
                "unmatched_reply_count": short_term_continuity_canary.get("metrics", {}).get(
                    "unmatched_reply_count",
                    "missing",
                ),
                "which_sentence_recurrence_count": short_term_continuity_canary.get("metrics", {}).get(
                    "which_sentence_recurrence_count",
                    "missing",
                ),
            },
            "short_term_recall_diagnostics": {
                "status": short_term_recall_diagnostics.get("status", "missing"),
                "primary_failure_class": short_term_recall_diagnostics.get("primary_failure_class", "missing"),
                "working_tail_status": short_term_recall_diagnostics.get("diagnostics", {}).get(
                    "working_tail_status",
                    "missing",
                ),
                "archive_fallback_status": short_term_recall_diagnostics.get("diagnostics", {}).get(
                    "archive_fallback_status",
                    "missing",
                ),
                "prompt_admission_status": short_term_recall_diagnostics.get("diagnostics", {}).get(
                    "prompt_admission_status",
                    "missing",
                ),
                "prompt_budget_status": short_term_recall_diagnostics.get("diagnostics", {}).get(
                    "prompt_budget_status",
                    "missing",
                ),
            },
            "qq_reply_integrity_diagnostics": {
                "status": qq_reply_integrity.get("status", "missing"),
                "visible_chat_reply_count": qq_reply_integrity.get("metrics", {}).get(
                    "visible_chat_reply_count",
                    "missing",
                ),
                "naked_ack_visible_reply_count": qq_reply_integrity.get("metrics", {}).get(
                    "naked_ack_visible_reply_count",
                    "missing",
                ),
                "visible_reply_missing_working_memory_count": qq_reply_integrity.get("metrics", {}).get(
                    "visible_reply_missing_working_memory_count",
                    "missing",
                ),
                "semantic_fast_direct_reply_count": qq_reply_integrity.get("metrics", {}).get(
                    "semantic_fast_direct_reply_count",
                    "missing",
                ),
                "semantic_fast_direct_reply_without_archive_count": qq_reply_integrity.get("metrics", {}).get(
                    "semantic_fast_direct_reply_without_archive_count",
                    "missing",
                ),
                "semantic_fast_direct_reply_without_visible_ack_count": qq_reply_integrity.get("metrics", {}).get(
                    "semantic_fast_direct_reply_without_visible_ack_count",
                    "missing",
                ),
                "working_memory_file_count": qq_reply_integrity.get("metrics", {}).get(
                    "working_memory_file_count",
                    "missing",
                ),
                "working_memory_row_count": qq_reply_integrity.get("metrics", {}).get(
                    "working_memory_row_count",
                    "missing",
                ),
            },
            "perception_event_layer": {
                "status": perception_event_layer.get("status", "missing"),
                "event_count": perception_event_layer.get("metrics", {}).get("event_count", "missing"),
                "source_count": perception_event_layer.get("metrics", {}).get("source_count", "missing"),
                "event_type_count": perception_event_layer.get("metrics", {}).get("event_type_count", "missing"),
                "input_event_count": perception_event_layer.get("metrics", {}).get("input_event_count", "missing"),
                "qq_event_count": perception_event_layer.get("metrics", {}).get("qq_event_count", "missing"),
                "desktop_event_count": perception_event_layer.get("metrics", {}).get("desktop_event_count", "missing"),
                "tool_result_event_count": perception_event_layer.get("metrics", {}).get(
                    "tool_result_event_count",
                    "missing",
                ),
                "system_health_event_count": perception_event_layer.get("metrics", {}).get(
                    "system_health_event_count",
                    "missing",
                ),
                "file_change_event_count": perception_event_layer.get("metrics", {}).get(
                    "file_change_event_count",
                    "missing",
                ),
                "visual_event_count": perception_event_layer.get("metrics", {}).get("visual_event_count", "missing"),
                "voice_event_count": perception_event_layer.get("metrics", {}).get("voice_event_count", "missing"),
                "importance_ready_count": perception_event_layer.get("metrics", {}).get(
                    "importance_ready_count",
                    "missing",
                ),
                "anomaly_count": perception_event_layer.get("metrics", {}).get("anomaly_count", "missing"),
                "latest_event_type": perception_event_layer.get("metrics", {}).get("latest_event_type", "missing"),
                "latest_event_source": perception_event_layer.get("metrics", {}).get(
                    "latest_event_source",
                    "missing",
                ),
                "latest_event_ref": perception_event_layer.get("metrics", {}).get("latest_event_ref", "missing"),
            },
            "perception_importance": {
                "status": perception_importance.get("status", "missing"),
                "event_count": perception_importance.get("metrics", {}).get("event_count", "missing"),
                "judged_event_count": perception_importance.get("metrics", {}).get(
                    "judged_event_count",
                    "missing",
                ),
                "high_attention_count": perception_importance.get("metrics", {}).get(
                    "high_attention_count",
                    "missing",
                ),
                "anomaly_judgment_count": perception_importance.get("metrics", {}).get(
                    "anomaly_judgment_count",
                    "missing",
                ),
                "internal_gap_count": perception_importance.get("metrics", {}).get(
                    "internal_gap_count",
                    "missing",
                ),
                "owner_attention_count": perception_importance.get("metrics", {}).get(
                    "owner_attention_count",
                    "missing",
                ),
                "repair_gap_count": perception_importance.get("metrics", {}).get("repair_gap_count", "missing"),
                "boundary_gap_count": perception_importance.get("metrics", {}).get(
                    "boundary_gap_count",
                    "missing",
                ),
                "action_residue_count": perception_importance.get("metrics", {}).get(
                    "action_residue_count",
                    "missing",
                ),
                "maintenance_gap_count": perception_importance.get("metrics", {}).get(
                    "maintenance_gap_count",
                    "missing",
                ),
                "coverage_gap_count": perception_importance.get("metrics", {}).get(
                    "coverage_gap_count",
                    "missing",
                ),
                "max_attention_weight": perception_importance.get("metrics", {}).get(
                    "max_attention_weight",
                    "missing",
                ),
                "latest_gap_type": perception_importance.get("metrics", {}).get("latest_gap_type", "missing"),
                "latest_future_effect": perception_importance.get("metrics", {}).get(
                    "latest_future_effect",
                    "missing",
                ),
                "next_route_hint": perception_importance.get("metrics", {}).get("next_route_hint", "missing"),
                "priority_gap_type": perception_signal.get("gap_type", "missing"),
                "priority_route_hint": perception_signal.get("route_hint", "missing"),
                "priority_future_effect": perception_signal.get("future_effect", "missing"),
                "priority_bias": perception_signal.get("bias", "missing"),
            },
            "action_feedback": {
                "feedback_signal": action_feedback_signal,
                "action_result": action_feedback_result,
                "future_effect": action_feedback_future,
                "scoring_effect": action_feedback.get("scoring_effect", "missing"),
                "memory_effect": action_feedback_memory,
                "stable_memory_write": action_feedback.get("stable_memory_write", "missing"),
                "raw_private_body_retained": action_feedback.get("raw_private_body_retained", "missing"),
                "visible_reply_text_retained": action_feedback.get("visible_reply_text_retained", "missing"),
            },
            "action_feedback_coverage": {
                "status": coverage_status,
                "observed_surface_count": coverage_observed_count,
                "non_qq_surface_count": coverage_non_qq_count,
                "future_effect_count": coverage_future_effect_count,
                "failure_count": coverage_failure_count,
                "latest_feedback_signal": coverage_metrics.get("latest_feedback_signal", "none"),
                "latest_feedback_surface": coverage_metrics.get("latest_feedback_surface", "none"),
                "latest_lifecycle_status": coverage_metrics.get("latest_lifecycle_status", "missing"),
                "qq_feedback_status": _surface_status(coverage_surfaces, "qq"),
                "desktop_feedback_status": _surface_status(coverage_surfaces, "desktop"),
                "codex_feedback_status": _surface_status(coverage_surfaces, "codex"),
                "local_tool_feedback_status": _surface_status(coverage_surfaces, "local_tool"),
                "patch_executor_feedback_status": _surface_status(coverage_surfaces, "patch_executor"),
                "code_probe_status": _surface_status(coverage_surfaces, "code_probe"),
                "runtime_probe_status": _surface_status(coverage_surfaces, "runtime_probe"),
                "qq_lifecycle_status": _surface_lifecycle(coverage_surfaces, "qq"),
                "desktop_lifecycle_status": _surface_lifecycle(coverage_surfaces, "desktop"),
                "codex_lifecycle_status": _surface_lifecycle(coverage_surfaces, "codex"),
                "local_tool_lifecycle_status": _surface_lifecycle(coverage_surfaces, "local_tool"),
                "patch_executor_lifecycle_status": _surface_lifecycle(coverage_surfaces, "patch_executor"),
                "code_probe_lifecycle_status": _surface_lifecycle(coverage_surfaces, "code_probe"),
                "runtime_probe_lifecycle_status": _surface_lifecycle(coverage_surfaces, "runtime_probe"),
            },
            "owner_feedback_effect": {
                "status": owner_effect_status,
                "latest_feedback_kind": owner_effect_signal,
                "owner_reaction": owner_feedback_effect.get("owner_reaction", "missing"),
                "expression_strategy_bias": owner_effect_expression,
                "intention_bias": owner_effect_bias,
                "future_effect": owner_effect_future,
                "repair_pressure_count": owner_feedback_effect.get("repair_pressure_count", "missing"),
                "success_count": owner_feedback_effect.get("success_count", "missing"),
                "success_streak": owner_feedback_effect.get("success_streak", "missing"),
                "promotion_signal": owner_feedback_effect.get("promotion_signal", "missing"),
                "feedback_event_ref": owner_feedback_effect.get("feedback_event_ref", "missing"),
                "owner_response_signal": owner_response_signal,
                "owner_response_source": owner_feedback_effect.get("owner_response_source", "missing"),
                "owner_response_strategy_bias": owner_response_strategy,
                "owner_response_intention_bias": owner_response_bias,
                "owner_response_future_effect": owner_response_future,
                "owner_response_event_ref": owner_feedback_effect.get("owner_response_event_ref", "missing"),
            },
            "proactive_response_diagnostics": {
                "status": proactive_response_status,
                "response_signal_candidate": proactive_response_signal,
                "request_status": proactive_response_diagnostics.get("request_status", "missing"),
                "request_answer_state": proactive_response_diagnostics.get("request_answer_state", "missing"),
                "last_ack_status": proactive_response_diagnostics.get("last_ack_status", "missing"),
                "delivery_level": proactive_response_diagnostics.get("delivery_level", "missing"),
                "delivered_waiting_owner": proactive_response_diagnostics.get("delivered_waiting_owner", "missing"),
                "timeout_active": proactive_response_diagnostics.get("timeout_active", "missing"),
                "age_minutes": proactive_response_diagnostics.get("age_minutes", "missing"),
                "minutes_until_no_response_timeout": proactive_response_diagnostics.get(
                    "minutes_until_no_response_timeout",
                    "missing",
                ),
                "next_no_response_timeout_at": proactive_response_diagnostics.get(
                    "next_no_response_timeout_at",
                    "missing",
                ),
                "future_effect_if_timeout": proactive_response_diagnostics.get(
                    "future_effect_if_timeout",
                    "missing",
                ),
                "request_event_ref": proactive_response_diagnostics.get("request_event_ref", "missing"),
            },
        },
        "privacy": {
            "raw_owner_text_in_report": False,
            "visible_reply_text_in_report": False,
            "stable_personality_claim": False,
            "consciousness_claim": False,
        },
    }


def render_autonomy_loop_report(report: dict[str, Any]) -> str:
    lines = [
        "# XinYu Autonomy Loop Report",
        "",
        f"- generated_at: {report.get('generated_at', 'unknown')}",
        f"- definition: {report.get('definition', 'unknown')}",
        f"- result: {'pass' if report.get('ok') else 'needs_check'}",
        "- claim_boundary: verifies closed-loop evidence only; does not claim consciousness",
        "",
        "## Main Loop Checks",
    ]
    for check in report.get("checks", []):
        state = "OK" if check.get("ok") else "WARN"
        required = "required" if check.get("required", True) else "optional"
        lines.append(
            f"- {state} {check.get('name')} ({required}; {check.get('stage')}): {check.get('detail')}"
        )
    state = report.get("state") if isinstance(report.get("state"), dict) else {}
    lines.extend(["", "## Current State"])
    for section_name in (
        "decision_chain",
        "intention",
        "attention",
        "relation",
        "self_thought",
        "short_term_continuity",
        "short_term_continuity_canary",
        "short_term_recall_diagnostics",
        "qq_reply_integrity_diagnostics",
        "perception_event_layer",
        "perception_importance",
        "action_feedback",
        "action_feedback_coverage",
        "owner_feedback_effect",
        "proactive_response_diagnostics",
    ):
        section = state.get(section_name) if isinstance(state.get(section_name), dict) else {}
        lines.append(f"### {section_name}")
        for key, value in section.items():
            lines.append(f"- {key}: {value}")
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    lines.extend(["", "## Privacy Boundary"])
    for key, value in privacy.items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def write_autonomy_loop_report(root: Path, report: dict[str, Any], *, output: Path | None = None) -> Path:
    return write_autonomy_loop_report_text(root, render_autonomy_loop_report(report), output=output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only XinYu main autonomy loop report.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--core-url", default=DEFAULT_CORE_URL)
    parser.add_argument("--window-minutes", type=int, default=DEFAULT_WINDOW_MINUTES)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--no-status", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    status_data: dict[str, Any] | None = None
    status_error = ""
    if not args.no_status:
        status_data, status_error = _load_live_status(root, args.core_url)
    report = build_autonomy_loop_report(
        root,
        status_data=status_data,
        status_error=status_error,
        window_minutes=max(1, int(args.window_minutes)),
    )
    if args.write:
        report["report_path"] = str(write_autonomy_loop_report(root, report, output=args.output))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_autonomy_loop_report(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
