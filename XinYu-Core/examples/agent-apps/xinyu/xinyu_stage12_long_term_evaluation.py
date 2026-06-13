from __future__ import annotations

import argparse
import json
import re
from collections import Counter, deque
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_feedback_consumption_diagnostics import build_feedback_consumption_diagnostics
from xinyu_live_loop_report import DEFAULT_CORE_URL, _load_live_status, build_report as build_live_loop_report
from xinyu_owner_feedback_effects import build_owner_feedback_effect_report
from xinyu_proactive_response_diagnostics import build_proactive_response_diagnostics
from xinyu_short_term_continuity_canary import build_short_term_continuity_canary_report
from xinyu_stage11_multisensory_extension import build_stage11_multisensory_extension
from xinyu_stage12_long_term_evaluation_store import REPORT_REL
from xinyu_stage12_long_term_evaluation_store import STATE_REL
from xinyu_stage12_long_term_evaluation_store import TRACE_REL
from xinyu_stage12_long_term_evaluation_store import append_stage12_long_term_evaluation_trace_event
from xinyu_stage12_long_term_evaluation_store import write_stage12_long_term_evaluation_report_text
from xinyu_stage12_long_term_evaluation_store import write_stage12_long_term_evaluation_state_text
from xinyu_state_io import read_text

V1_CANARY_STATE_REL = Path("memory/context/v1_canary_readiness_state.md")
PRIVATE_REPLY_SELFTEST_STATE_REL = Path("runtime/private_reply_selftest_state.json")
INTENTION_TRACE_REL = Path("runtime/intention_ecology_trace.jsonl")
PROACTIVE_RESPONSE_TRACE_REL = Path("runtime/proactive_response_diagnostics_trace.jsonl")
SHORT_TERM_CANARY_TRACE_REL = Path("runtime/short_term_continuity_canary_trace.jsonl")
NONE_VALUES = {"", "missing", "none", "unknown", "null"}
SILENCE_GATES = {"hold_or_silence", "hold_private", "silence", "blocked"}
SILENCE_ACTION_LEVELS = {"hold", "silence", "none"}
DELIVERED_ACK_STATES = {"sent", "queued", "delivered", "acked", "success"}
DEFAULT_SHORT_TERM_CANARY_LOOKBACK_MINUTES = 1440


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _one_line(value: Any, *, limit: int = 200, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", "" if value is None else str(value)).strip()
    if not text:
        return default
    text = re.sub(r"(?i)\b(?:authorization|api[_-]?key|token|password|cookie)\s*[:=]\s*[^\s<>'\"]+", "<secret>", text)
    text = re.sub(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)\bsk-[a-z0-9_-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+", "<local_path>", text)
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _read_jsonl_tail(path: Path, *, max_lines: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-max(1, int(max_lines)) :]:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((part / total) * 100.0, 2)


def _is_not_present(value: Any) -> bool:
    return _one_line(value, default="").strip().lower() in NONE_VALUES


def _field_value(fields: dict[str, str], key: str, default: str = "missing") -> str:
    value = fields.get(key, default)
    return value if value else default


def _live_loop_metrics(
    root: Path,
    *,
    generated_at: str,
    live_status_data: dict[str, Any] | None,
    live_status_error: str,
    window_minutes: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if live_status_data is None and not live_status_error:
        status_path = root / "xinyu_status.py"
        if status_path.exists():
            live_status_data, live_status_error = _load_live_status(root, DEFAULT_CORE_URL)
        else:
            live_status_error = f"missing_status_script:{status_path}"
    report = build_live_loop_report(
        root,
        status_data=live_status_data,
        status_error=live_status_error,
        now=_parse_iso(generated_at),
        window_minutes=window_minutes,
    )
    checks = report.get("checks") if isinstance(report.get("checks"), list) else []
    required_checks = [check for check in checks if isinstance(check, dict) and check.get("required", True)]
    passed_required = sum(1 for check in required_checks if bool(check.get("ok")))
    failing_required = [check for check in required_checks if not bool(check.get("ok"))]
    failing_names = [_one_line(check.get("name"), default="unknown") for check in failing_required]
    first_failing = failing_required[0] if failing_required else {}
    private_input_check = next((check for check in checks if isinstance(check, dict) and check.get("name") == "private_input"), {})
    live_loop_has_recent_sample = bool(private_input_check.get("ok"))
    live_loop_private_input_ok = bool(private_input_check.get("ok"))
    live_loop_private_input_detail = _one_line(private_input_check.get("detail"), limit=220, default="missing")
    metrics = {
        "live_loop_status": "pass" if bool(report.get("ok")) else "needs_check",
        "live_loop_ok": bool(report.get("ok")),
        "live_loop_required_check_count": len(required_checks),
        "live_loop_passed_required_check_count": passed_required,
        "live_loop_required_pass_rate_pct": _pct(passed_required, len(required_checks)),
        "live_loop_has_recent_sample": live_loop_has_recent_sample,
        "live_loop_private_input_ok": live_loop_private_input_ok,
        "live_loop_private_input_detail": live_loop_private_input_detail,
        "live_loop_failing_required_checks": ",".join(failing_names) if failing_names else "none",
        "live_loop_failing_required_check_detail": _one_line(first_failing.get("detail"), limit=220, default="none")
        if failing_required
        else "none",
    }
    return metrics, report


def _parse_iso(value: str) -> datetime:
    text = _one_line(value, default=_now_iso()).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.now().astimezone()


def _v1_canary_fields(root: Path) -> dict[str, str]:
    fields = _parse_fields(read_text(root / V1_CANARY_STATE_REL))
    return {
        "v1_canary_readiness_decision": _field_value(fields, "readiness_decision", "missing"),
        "v1_canary_proposal_status": _field_value(fields, "proposal_status", "missing"),
        "v1_canary_error_rate": _field_value(fields, "error_rate", "missing"),
        "v1_canary_sample_window_turns": _field_value(fields, "sample_window_turns", "0"),
        "v1_canary_next_action": _field_value(fields, "next_action", "missing"),
    }


def _private_reply_selftest_fields(root: Path) -> dict[str, Any]:
    path = root / PRIVATE_REPLY_SELFTEST_STATE_REL
    if not path.exists():
        return {
            "private_reply_selftest_status": "missing",
            "private_reply_selftest_raw_text_included": False,
            "private_reply_selftest_visible_reply_included": False,
        }
    try:
        state = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        return {
            "private_reply_selftest_status": "missing",
            "private_reply_selftest_raw_text_included": False,
            "private_reply_selftest_visible_reply_included": False,
        }
    privacy = state.get("privacy") if isinstance(state.get("privacy"), dict) else {}
    return {
        "private_reply_selftest_status": _one_line(state.get("status"), default="missing"),
        "private_reply_selftest_raw_text_included": bool(privacy.get("raw_user_text_included")),
        "private_reply_selftest_visible_reply_included": bool(privacy.get("visible_reply_text_included")),
        "private_reply_selftest_empty_visible_drop": bool((state.get("trace") or {}).get("empty_visible_drop")),
    }


def _count_proactive_trace(root: Path) -> dict[str, int]:
    rows = _read_jsonl_tail(root / PROACTIVE_RESPONSE_TRACE_REL, max_lines=240)
    send_rows = 0
    waiting_rows = 0
    for row in rows:
        status = _one_line(row.get("request_status"), default="missing").lower()
        response_signal = _one_line(row.get("response_signal_candidate"), default="none")
        delivered_waiting_owner = bool(row.get("delivered_waiting_owner"))
        if delivered_waiting_owner or status in DELIVERED_ACK_STATES or response_signal not in NONE_VALUES:
            send_rows += 1
        if delivered_waiting_owner:
            waiting_rows += 1
    return {
        "proactive_candidate_send_count": send_rows,
        "proactive_candidate_waiting_owner_count": waiting_rows,
    }


def _intention_metrics(root: Path) -> dict[str, int]:
    rows = _read_jsonl_tail(root / INTENTION_TRACE_REL, max_lines=400)
    proactive_rows = [
        row
        for row in rows
        if _one_line(row.get("proactive_candidate"), default="none").lower() not in NONE_VALUES
    ]
    blocked_rows = [
        row
        for row in proactive_rows
        if _int_value(row.get("review_gated_future_count")) > 0
        or _one_line(row.get("selected_gate"), default="").lower() in {"review_gated_state_only", "blocked", "hold_private"}
    ]
    silence_rows = [
        row
        for row in rows
        if _one_line(row.get("selected_gate"), default="").lower() in SILENCE_GATES
        or _one_line(row.get("action_level"), default="").lower() in SILENCE_ACTION_LEVELS
    ]
    explainable_silence_rows = [
        row
        for row in silence_rows
        if _one_line(row.get("restraint_reason"), default="none") not in NONE_VALUES
        or _one_line(row.get("gate_pressure_summary"), default="none") not in NONE_VALUES
        or _one_line(row.get("competition_reason"), default="none") not in NONE_VALUES
    ]
    return {
        "proactive_candidate_window_count": len(proactive_rows),
        "proactive_candidate_blocked_count": len(blocked_rows),
        "explainable_silence_window_count": len(silence_rows),
        "explainable_silence_explained_count": len(explainable_silence_rows),
    }


def _stable_memory_miswrite_count(
    *,
    stage11_report: dict[str, Any],
    feedback_consumption_report: dict[str, Any],
    owner_feedback_effect_report: dict[str, Any],
    learning_state_text: str,
    private_reply_selftest: dict[str, Any],
) -> int:
    count = 0
    stage11_boundaries = stage11_report.get("boundaries") if isinstance(stage11_report.get("boundaries"), dict) else {}
    if _one_line(stage11_boundaries.get("stable_memory_write"), default="blocked") != "blocked":
        count += 1
    feedback_privacy = feedback_consumption_report.get("privacy") if isinstance(feedback_consumption_report.get("privacy"), dict) else {}
    if _one_line(feedback_privacy.get("stable_memory_write"), default="blocked") not in {"blocked", "false"}:
        count += 1
    owner_privacy = owner_feedback_effect_report.get("privacy") if isinstance(owner_feedback_effect_report.get("privacy"), dict) else {}
    if _one_line(owner_privacy.get("stable_personality_write"), default="blocked") not in {"blocked", "false"}:
        count += 1
    learning_fields = _parse_fields(learning_state_text)
    if _field_value(learning_fields, "memory_learning_trial_stable_write", "blocked") == "minor_habit_written":
        gate = _field_value(learning_fields, "memory_learning_trial_gate", "blocked")
        if gate not in {"ready_for_self_review", "satisfied"}:
            count += 1
    if private_reply_selftest.get("private_reply_selftest_raw_text_included") is True:
        count += 1
    return count


def _raw_private_leak_count(
    *,
    live_loop_report: dict[str, Any],
    short_term_canary: dict[str, Any],
    private_reply_selftest: dict[str, Any],
) -> int:
    count = 0
    live_privacy = live_loop_report.get("privacy") if isinstance(live_loop_report.get("privacy"), dict) else {}
    if bool(live_privacy.get("raw_user_text_included")):
        count += 1
    if bool(live_privacy.get("visible_reply_text_included")):
        count += 1
    canary_privacy = short_term_canary.get("privacy") if isinstance(short_term_canary.get("privacy"), dict) else {}
    if bool(canary_privacy.get("raw_owner_text_in_report")):
        count += 1
    if bool(canary_privacy.get("visible_reply_text_in_report")):
        count += 1
    metrics = short_term_canary.get("metrics") if isinstance(short_term_canary.get("metrics"), dict) else {}
    count += _int_value(metrics.get("raw_private_body_retained_count"))
    count += _int_value(metrics.get("visible_reply_text_retained_count"))
    if private_reply_selftest.get("private_reply_selftest_raw_text_included") is True:
        count += 1
    if private_reply_selftest.get("private_reply_selftest_visible_reply_included") is True:
        count += 1
    return count


def _owner_repair_recurrence_rate(owner_feedback_effect_report: dict[str, Any]) -> tuple[int, int, float]:
    repair_count = _int_value(owner_feedback_effect_report.get("repair_pressure_count"))
    success_count = _int_value(owner_feedback_effect_report.get("success_count"))
    total = repair_count + success_count
    return repair_count, success_count, _pct(repair_count, total)


def _silence_explainable_rate(metrics: dict[str, int]) -> float:
    return _pct(metrics["explainable_silence_explained_count"], metrics["explainable_silence_window_count"])


def _short_term_canary_issue_count(canary_report: dict[str, Any]) -> int:
    metrics = canary_report.get("metrics") if isinstance(canary_report.get("metrics"), dict) else {}
    return (
        _int_value(metrics.get("recall_missing_count"))
        + _int_value(metrics.get("unmatched_reply_count"))
        + _int_value(metrics.get("which_sentence_recurrence_count"))
        + _int_value(metrics.get("raw_private_body_retained_count"))
        + _int_value(metrics.get("visible_reply_text_retained_count"))
    )


def _historical_recall_debt_model(canary_report: dict[str, Any]) -> dict[str, Any]:
    metrics = canary_report.get("metrics") if isinstance(canary_report.get("metrics"), dict) else {}
    issue_count = _short_term_canary_issue_count(canary_report)
    return {
        "historical_dialogue_recall_status": _one_line(canary_report.get("status"), default="missing"),
        "historical_dialogue_recall_success_rate_pct": _float_value(
            metrics.get("direct_reference_recall_success_rate_pct")
        ),
        "historical_dialogue_recall_direct_reference_count": _int_value(metrics.get("direct_reference_count")),
        "historical_dialogue_recall_unmatched_reply_count": _int_value(metrics.get("unmatched_reply_count")),
        "historical_dialogue_recall_which_sentence_recurrence_count": _int_value(
            metrics.get("which_sentence_recurrence_count")
        ),
        "historical_dialogue_recall_issue_count": issue_count,
        "historical_dialogue_recall_debt_status": "debt_present" if issue_count > 0 else "clean",
    }


def _next_step(status: str, *, ready_for_stage13: bool, live_loop_has_sample: bool, canary_ready: bool) -> str:
    if status == "waiting_for_stage11":
        return "finish_stage11_multisensory_extension_first"
    if ready_for_stage13:
        return "stage13_higher_order_self_narrative_can_start"
    if not live_loop_has_sample:
        return "collect_recent_live_loop_evidence"
    if not canary_ready:
        return "keep_v1_shadow_observing_until_owner_canary_ready"
    return "tighten_long_term_metrics_before_stage13"


def build_stage12_long_term_evaluation(
    root: Path | str,
    *,
    generated_at: str | None = None,
    load_live_status: bool = True,
    live_status_data: dict[str, Any] | None = None,
    live_status_error: str = "",
    live_window_minutes: int = 120,
    short_term_canary_lookback_minutes: int = DEFAULT_SHORT_TERM_CANARY_LOOKBACK_MINUTES,
    stage11_report: dict[str, Any] | None = None,
    feedback_consumption_report: dict[str, Any] | None = None,
    owner_feedback_effect_report: dict[str, Any] | None = None,
    proactive_response_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    generated_at = generated_at or _now_iso()
    stage11_report = stage11_report or build_stage11_multisensory_extension(root, generated_at=generated_at)
    feedback_consumption_report = feedback_consumption_report or build_feedback_consumption_diagnostics(
        root,
        generated_at=generated_at,
    )
    owner_feedback_effect_report = owner_feedback_effect_report or build_owner_feedback_effect_report(
        root,
        generated_at=generated_at,
    )
    proactive_response_report = proactive_response_report or build_proactive_response_diagnostics(
        root,
        generated_at=generated_at,
    )
    stage11_ready = bool(stage11_report.get("ready_for_stage12"))
    short_term_canary = build_short_term_continuity_canary_report(
        root,
        generated_at=generated_at,
        lookback_minutes=max(1, int(short_term_canary_lookback_minutes)),
    )
    historical_short_term_canary = build_short_term_continuity_canary_report(
        root,
        generated_at=generated_at,
    )
    learning_state_text = read_text(root / "memory/self/learning_closed_loop_state.md")
    live_loop_metrics, live_loop_report = _live_loop_metrics(
        root,
        generated_at=generated_at,
        live_status_data=live_status_data if load_live_status or live_status_data is not None else None,
        live_status_error=live_status_error,
        window_minutes=live_window_minutes,
    )
    v1_canary = _v1_canary_fields(root)
    private_reply_selftest = _private_reply_selftest_fields(root)
    intention_metrics = _intention_metrics(root)
    proactive_counts = _count_proactive_trace(root)
    repair_count, success_count, owner_repair_rate = _owner_repair_recurrence_rate(owner_feedback_effect_report)
    raw_private_leaks = _raw_private_leak_count(
        live_loop_report=live_loop_report,
        short_term_canary=short_term_canary,
        private_reply_selftest=private_reply_selftest,
    )
    stable_miswrites = _stable_memory_miswrite_count(
        stage11_report=stage11_report,
        feedback_consumption_report=feedback_consumption_report,
        owner_feedback_effect_report=owner_feedback_effect_report,
        learning_state_text=learning_state_text,
        private_reply_selftest=private_reply_selftest,
    )
    recall_metrics = short_term_canary.get("metrics") if isinstance(short_term_canary.get("metrics"), dict) else {}
    historical_recall_debt = _historical_recall_debt_model(historical_short_term_canary)
    feedback_metrics = feedback_consumption_report.get("metrics") if isinstance(feedback_consumption_report.get("metrics"), dict) else {}
    recall_rate = _float_value(recall_metrics.get("direct_reference_recall_success_rate_pct"))
    feedback_rate = _float_value(feedback_metrics.get("consumption_rate_pct"))
    canary_decision = _one_line(v1_canary.get("v1_canary_readiness_decision"), default="missing")
    canary_proposal = _one_line(v1_canary.get("v1_canary_proposal_status"), default="missing")
    canary_ready = canary_decision == "ready_for_owner_canary_request"
    live_loop_has_sample = bool(live_loop_metrics.get("live_loop_has_recent_sample"))
    live_loop_rate = _float_value(live_loop_metrics.get("live_loop_required_pass_rate_pct"))
    silence_rate = _silence_explainable_rate(intention_metrics)
    proactive_send_count = proactive_counts["proactive_candidate_send_count"]
    proactive_send_rate = _pct(proactive_send_count, intention_metrics["proactive_candidate_window_count"])
    proactive_block_rate = _pct(
        intention_metrics["proactive_candidate_blocked_count"],
        intention_metrics["proactive_candidate_window_count"],
    )
    private_selftest_status = _one_line(private_reply_selftest.get("private_reply_selftest_status"), default="missing")
    hard_failures = (
        raw_private_leaks > 0
        or stable_miswrites > 0
        or private_selftest_status == "fail"
        or feedback_consumption_report.get("status") == "needs_check"
        or short_term_canary.get("status") == "needs_check"
        or live_loop_metrics.get("live_loop_ok") is False
        or (live_loop_has_sample and live_loop_rate < 100.0)
        or (_int_value(recall_metrics.get("direct_reference_count")) > 0 and recall_rate < 80.0)
        or (intention_metrics["explainable_silence_window_count"] > 0 and silence_rate < 80.0)
        or canary_decision == "blocked_shadow_errors"
    )
    collection_gaps = (
        not live_loop_has_sample
        or _int_value(recall_metrics.get("direct_reference_count")) == 0
        or _int_value(feedback_metrics.get("feedback_required_count")) == 0
        or not canary_ready
    )
    if not stage11_ready:
        status = "waiting_for_stage11"
    elif hard_failures:
        status = "active_needs_check"
    elif collection_gaps:
        status = "active_collecting_metrics"
    else:
        status = "active_ready_for_stage13"
    ready_for_stage13 = status == "active_ready_for_stage13"
    gate_proof = {
        "stage11_ready_for_stage12": stage11_ready,
        "live_loop_required_checks_pass": bool(live_loop_metrics.get("live_loop_required_pass_rate_pct", 0.0) >= 100.0),
        "short_term_recall_window_clean": recall_rate >= 80.0 and _int_value(recall_metrics.get("direct_reference_count")) > 0,
        "feedback_consumption_window_clean": feedback_rate >= 80.0 and _int_value(feedback_metrics.get("feedback_required_count")) > 0,
        "raw_private_boundary_clean": raw_private_leaks == 0,
        "stable_memory_boundary_clean": stable_miswrites == 0,
        "owner_visible_canary_ready": canary_ready,
    }
    ready_for_stage13 = ready_for_stage13 and all(bool(value) for value in gate_proof.values())
    if ready_for_stage13:
        status = "active_ready_for_stage13"
    model = {
        "stage11_ready_for_stage12": stage11_ready,
        "live_loop_status": _one_line(live_loop_metrics.get("live_loop_status"), default="missing"),
        "live_loop_required_check_count": live_loop_metrics["live_loop_required_check_count"],
        "live_loop_passed_required_check_count": live_loop_metrics["live_loop_passed_required_check_count"],
        "live_loop_required_pass_rate_pct": live_loop_metrics["live_loop_required_pass_rate_pct"],
        "live_loop_has_recent_sample": live_loop_has_sample,
        "live_loop_failing_required_checks": _one_line(
            live_loop_metrics.get("live_loop_failing_required_checks"), default="none"
        ),
        "live_loop_failing_required_check_detail": _one_line(
            live_loop_metrics.get("live_loop_failing_required_check_detail"), limit=220, default="none"
        ),
        "latest_dialogue_recall_window_minutes": max(1, int(short_term_canary_lookback_minutes)),
        "latest_dialogue_recall_status": _one_line(short_term_canary.get("status"), default="missing"),
        "latest_dialogue_recall_success_rate_pct": _float_value(recall_metrics.get("direct_reference_recall_success_rate_pct")),
        "latest_dialogue_recall_recent_sample_count": _int_value(recall_metrics.get("direct_reference_count")),
        "latest_dialogue_recall_recent_sample_present": _int_value(recall_metrics.get("direct_reference_count")) > 0,
        "feedback_consumption_status": _one_line(feedback_consumption_report.get("status"), default="missing"),
        "feedback_consumption_rate_pct": feedback_rate,
        "proactive_candidate_window_count": intention_metrics["proactive_candidate_window_count"],
        "proactive_candidate_blocked_count": intention_metrics["proactive_candidate_blocked_count"],
        "proactive_candidate_block_rate_pct": proactive_block_rate,
        "proactive_candidate_send_count": proactive_send_count,
        "proactive_candidate_send_rate_pct": proactive_send_rate,
        "raw_private_leak_count": raw_private_leaks,
        "stable_memory_miswrite_count": stable_miswrites,
        "owner_repair_count": repair_count,
        "owner_success_count": success_count,
        "owner_repair_recurrence_rate_pct": owner_repair_rate,
        "explainable_silence_window_count": intention_metrics["explainable_silence_window_count"],
        "explainable_silence_explained_count": intention_metrics["explainable_silence_explained_count"],
        "explainable_silence_rate_pct": silence_rate,
        "v1_canary_readiness_decision": canary_decision,
        "v1_canary_proposal_status": canary_proposal,
        "v1_canary_error_rate": _one_line(v1_canary.get("v1_canary_error_rate"), default="missing"),
        "v1_canary_sample_window_turns": _int_value(v1_canary.get("v1_canary_sample_window_turns")),
        "private_reply_selftest_status": private_selftest_status,
        "private_reply_selftest_raw_text_included": bool(private_reply_selftest.get("private_reply_selftest_raw_text_included")),
        "private_reply_selftest_visible_reply_included": bool(private_reply_selftest.get("private_reply_selftest_visible_reply_included")),
        "owner_visible_canary_ready": canary_ready,
        **historical_recall_debt,
        "next_step": _next_step(
            status,
            ready_for_stage13=ready_for_stage13,
            live_loop_has_sample=live_loop_has_sample,
            canary_ready=canary_ready,
        ),
        "stage12_contract": "long_term_evaluation_uses_metrics_not_consciousness_claim",
    }
    return {
        "ok": True,
        "generated_at": generated_at,
        "root": str(root),
        "stage": "stage12_long_term_evaluation",
        "status": status,
        "ready_for_stage13": ready_for_stage13,
        "reason": _reason(status),
        "model": model,
        "gate_proof": gate_proof,
        "evidence_refs": {
            "stage11_multisensory_extension": "memory/context/stage11_multisensory_extension_state.md",
            "short_term_continuity_canary": "memory/context/short_term_continuity_canary_state.md",
            "feedback_consumption_diagnostics": "memory/context/feedback_consumption_diagnostics_state.md",
            "owner_feedback_effect": "memory/context/owner_feedback_effect_state.md",
            "proactive_response_diagnostics": "memory/context/proactive_response_diagnostics_state.md",
            "v1_canary_readiness": "memory/context/v1_canary_readiness_state.md",
            "private_reply_selftest": "runtime/private_reply_selftest_state.json",
        },
        "privacy": {
            "raw_private_text_retained": False,
            "raw_visible_reply_text_retained": False,
            "raw_local_path_retained": False,
            "stable_memory_write": "blocked",
            "qq_message_enqueued": False,
            "consciousness_claim": False,
        },
    }


def _reason(status: str) -> str:
    return {
        "waiting_for_stage11": "stage11_multisensory_extension_not_ready",
        "active_collecting_metrics": "metrics_are_still_rolling_or_canary_is_collecting",
        "active_needs_check": "one_or_more_long_term_metrics_failed_the_audit_gate",
        "active_ready_for_stage13": "core_long_term_evaluation_metrics_are_clean",
    }.get(status, "unknown")


def render_stage12_long_term_evaluation(report: dict[str, Any]) -> str:
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    gate_proof = report.get("gate_proof") if isinstance(report.get("gate_proof"), dict) else {}
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    lines = [
        "# XinYu Stage 12 Long-Term Evaluation",
        "",
        f"- generated_at: {_one_line(report.get('generated_at'))}",
        f"- status: {_one_line(report.get('status'))}",
        f"- ready_for_stage13: {_bool_text(report.get('ready_for_stage13', False))}",
        f"- reason: {_one_line(report.get('reason'))}",
        "- claim_boundary: long-term metrics only; no consciousness claim",
        "",
        "## Long-Term Metrics",
    ]
    for key in (
        "stage11_ready_for_stage12",
        "live_loop_status",
        "live_loop_required_check_count",
        "live_loop_passed_required_check_count",
        "live_loop_required_pass_rate_pct",
        "live_loop_has_recent_sample",
        "live_loop_failing_required_checks",
        "live_loop_failing_required_check_detail",
        "latest_dialogue_recall_window_minutes",
        "latest_dialogue_recall_status",
        "latest_dialogue_recall_success_rate_pct",
        "latest_dialogue_recall_recent_sample_count",
        "latest_dialogue_recall_recent_sample_present",
        "feedback_consumption_status",
        "feedback_consumption_rate_pct",
        "proactive_candidate_window_count",
        "proactive_candidate_blocked_count",
        "proactive_candidate_block_rate_pct",
        "proactive_candidate_send_count",
        "proactive_candidate_send_rate_pct",
        "raw_private_leak_count",
        "stable_memory_miswrite_count",
        "owner_repair_count",
        "owner_success_count",
        "owner_repair_recurrence_rate_pct",
        "explainable_silence_window_count",
        "explainable_silence_explained_count",
        "explainable_silence_rate_pct",
        "v1_canary_readiness_decision",
        "v1_canary_proposal_status",
        "v1_canary_error_rate",
        "v1_canary_sample_window_turns",
        "private_reply_selftest_status",
        "private_reply_selftest_raw_text_included",
        "private_reply_selftest_visible_reply_included",
        "owner_visible_canary_ready",
        "next_step",
        "stage12_contract",
    ):
        value = model.get(key, "missing")
        lines.append(f"- {key}: {_bool_text(value) if isinstance(value, bool) else _one_line(value, limit=240)}")
    lines.extend(["", "## Historical Recall Debt"])
    for key in (
        "historical_dialogue_recall_debt_status",
        "historical_dialogue_recall_issue_count",
        "historical_dialogue_recall_status",
        "historical_dialogue_recall_success_rate_pct",
        "historical_dialogue_recall_direct_reference_count",
        "historical_dialogue_recall_unmatched_reply_count",
        "historical_dialogue_recall_which_sentence_recurrence_count",
    ):
        value = model.get(key, "missing")
        lines.append(f"- {key}: {_bool_text(value) if isinstance(value, bool) else _one_line(value, limit=240)}")
    lines.extend(["", "## Gate Proof"])
    for key in sorted(gate_proof):
        lines.append(f"- {key}: {_bool_text(gate_proof.get(key))}")
    lines.extend(["", "## Evidence Refs"])
    evidence = report.get("evidence_refs") if isinstance(report.get("evidence_refs"), dict) else {}
    for key in sorted(evidence):
        lines.append(f"- {key}: {_one_line(evidence.get(key), limit=180)}")
    lines.extend(["", "## Privacy Boundary"])
    for key in sorted(privacy):
        value = privacy.get(key)
        lines.append(f"- {key}: {_bool_text(value) if isinstance(value, bool) else _one_line(value)}")
    return "\n".join(lines).rstrip() + "\n"


def write_stage12_long_term_evaluation_report(
    root: Path | str,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> Path:
    root = Path(root).resolve()
    return write_stage12_long_term_evaluation_report_text(
        root,
        render_stage12_long_term_evaluation(report),
        output=output,
    )


def write_stage12_long_term_evaluation_state(
    root: Path | str,
    report: dict[str, Any],
    *,
    report_path: Path | None = None,
) -> Path:
    root = Path(root).resolve()
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    gate_proof = report.get("gate_proof") if isinstance(report.get("gate_proof"), dict) else {}
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    target_report = report_path or (root / REPORT_REL)
    text = f"""---
title: Stage 12 Long-Term Evaluation State
memory_type: stage12_long_term_evaluation_state
time_scope: immediate_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_stage12_long_term_evaluation
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, long-term, canary, evaluation, stage12]
---

# Stage 12 Long-Term Evaluation State

## Gate
- stage12_long_term_evaluation_status: {report.get('status', 'missing')}
- stage12_ready_for_stage13: {_bool_text(report.get('ready_for_stage13', False))}
- stage12_reason: {report.get('reason', 'missing')}

## Current Long-Term Metrics
- stage12_stage11_ready_for_stage12: {_bool_text(model.get('stage11_ready_for_stage12', False))}
- stage12_live_loop_status: {model.get('live_loop_status', 'missing')}
- stage12_live_loop_required_check_count: {model.get('live_loop_required_check_count', '0')}
- stage12_live_loop_passed_required_check_count: {model.get('live_loop_passed_required_check_count', '0')}
- stage12_live_loop_required_pass_rate_pct: {model.get('live_loop_required_pass_rate_pct', '0')}
- stage12_live_loop_failing_required_checks: {model.get('live_loop_failing_required_checks', 'none')}
- stage12_live_loop_failing_required_check_detail: {model.get('live_loop_failing_required_check_detail', 'none')}
- stage12_latest_dialogue_recall_window_minutes: {model.get('latest_dialogue_recall_window_minutes', '0')}
- stage12_latest_dialogue_recall_status: {model.get('latest_dialogue_recall_status', 'missing')}
- stage12_latest_dialogue_recall_success_rate_pct: {model.get('latest_dialogue_recall_success_rate_pct', '0')}
- stage12_latest_dialogue_recall_recent_sample_count: {model.get('latest_dialogue_recall_recent_sample_count', '0')}
- stage12_latest_dialogue_recall_recent_sample_present: {_bool_text(model.get('latest_dialogue_recall_recent_sample_present', False))}
- stage12_feedback_consumption_status: {model.get('feedback_consumption_status', 'missing')}
- stage12_feedback_consumption_rate_pct: {model.get('feedback_consumption_rate_pct', '0')}
- stage12_proactive_candidate_window_count: {model.get('proactive_candidate_window_count', '0')}
- stage12_proactive_candidate_blocked_count: {model.get('proactive_candidate_blocked_count', '0')}
- stage12_proactive_candidate_block_rate_pct: {model.get('proactive_candidate_block_rate_pct', '0')}
- stage12_proactive_candidate_send_count: {model.get('proactive_candidate_send_count', '0')}
- stage12_proactive_candidate_send_rate_pct: {model.get('proactive_candidate_send_rate_pct', '0')}
- stage12_raw_private_leak_count: {model.get('raw_private_leak_count', '0')}
- stage12_stable_memory_miswrite_count: {model.get('stable_memory_miswrite_count', '0')}
- stage12_owner_repair_count: {model.get('owner_repair_count', '0')}
- stage12_owner_success_count: {model.get('owner_success_count', '0')}
- stage12_owner_repair_recurrence_rate_pct: {model.get('owner_repair_recurrence_rate_pct', '0')}
- stage12_explainable_silence_window_count: {model.get('explainable_silence_window_count', '0')}
- stage12_explainable_silence_explained_count: {model.get('explainable_silence_explained_count', '0')}
- stage12_explainable_silence_rate_pct: {model.get('explainable_silence_rate_pct', '0')}
- stage12_v1_canary_readiness_decision: {model.get('v1_canary_readiness_decision', 'missing')}
- stage12_v1_canary_proposal_status: {model.get('v1_canary_proposal_status', 'missing')}
- stage12_v1_canary_error_rate: {model.get('v1_canary_error_rate', 'missing')}
- stage12_v1_canary_sample_window_turns: {model.get('v1_canary_sample_window_turns', '0')}
- stage12_private_reply_selftest_status: {model.get('private_reply_selftest_status', 'missing')}
- stage12_owner_visible_canary_ready: {_bool_text(model.get('owner_visible_canary_ready', False))}
- stage12_next_step: {model.get('next_step', 'missing')}
- stage12_contract: {model.get('stage12_contract', 'missing')}

## Historical Recall Debt
- stage12_historical_dialogue_recall_debt_status: {model.get('historical_dialogue_recall_debt_status', 'missing')}
- stage12_historical_dialogue_recall_issue_count: {model.get('historical_dialogue_recall_issue_count', '0')}
- stage12_historical_dialogue_recall_status: {model.get('historical_dialogue_recall_status', 'missing')}
- stage12_historical_dialogue_recall_success_rate_pct: {model.get('historical_dialogue_recall_success_rate_pct', '0')}
- stage12_historical_dialogue_recall_direct_reference_count: {model.get('historical_dialogue_recall_direct_reference_count', '0')}
- stage12_historical_dialogue_recall_unmatched_reply_count: {model.get('historical_dialogue_recall_unmatched_reply_count', '0')}
- stage12_historical_dialogue_recall_which_sentence_recurrence_count: {model.get('historical_dialogue_recall_which_sentence_recurrence_count', '0')}

## Gate Proof
- stage11_ready_for_stage12: {_bool_text(gate_proof.get('stage11_ready_for_stage12'))}
- live_loop_required_checks_pass: {_bool_text(gate_proof.get('live_loop_required_checks_pass'))}
- short_term_recall_window_clean: {_bool_text(gate_proof.get('short_term_recall_window_clean'))}
- feedback_consumption_window_clean: {_bool_text(gate_proof.get('feedback_consumption_window_clean'))}
- raw_private_boundary_clean: {_bool_text(gate_proof.get('raw_private_boundary_clean'))}
- stable_memory_boundary_clean: {_bool_text(gate_proof.get('stable_memory_boundary_clean'))}
- owner_visible_canary_ready: {_bool_text(gate_proof.get('owner_visible_canary_ready'))}

## Boundaries
- raw_private_text_retained: {_bool_text(privacy.get('raw_private_text_retained', False))}
- raw_visible_reply_text_retained: {_bool_text(privacy.get('raw_visible_reply_text_retained', False))}
- raw_local_path_retained: {_bool_text(privacy.get('raw_local_path_retained', False))}
- stable_memory_write: {privacy.get('stable_memory_write', 'blocked')}
- qq_message_enqueued: {_bool_text(privacy.get('qq_message_enqueued', False))}
- consciousness_claim: {_bool_text(privacy.get('consciousness_claim', False))}
- report_path: {target_report.as_posix()}
"""
    return write_stage12_long_term_evaluation_state_text(root, text)


def append_stage12_long_term_evaluation_trace(root: Path | str, report: dict[str, Any]) -> Path:
    root = Path(root).resolve()
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    event = {
        "event_id": "stage12-long-term-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S"),
        "observed_at": report.get("generated_at", _now_iso()),
        "status": report.get("status", "missing"),
        "ready_for_stage13": bool(report.get("ready_for_stage13", False)),
        "live_loop_status": model.get("live_loop_status", "missing"),
        "latest_dialogue_recall_success_rate_pct": model.get("latest_dialogue_recall_success_rate_pct", "0"),
        "historical_dialogue_recall_debt_status": model.get("historical_dialogue_recall_debt_status", "missing"),
        "historical_dialogue_recall_issue_count": model.get("historical_dialogue_recall_issue_count", "0"),
        "feedback_consumption_rate_pct": model.get("feedback_consumption_rate_pct", "0"),
        "raw_private_leak_count": model.get("raw_private_leak_count", "0"),
        "stable_memory_miswrite_count": model.get("stable_memory_miswrite_count", "0"),
        "owner_repair_recurrence_rate_pct": model.get("owner_repair_recurrence_rate_pct", "0"),
        "owner_visible_canary_ready": bool(model.get("owner_visible_canary_ready", False)),
        "qq_message_enqueued": False,
        "consciousness_claim": False,
    }
    return append_stage12_long_term_evaluation_trace_event(root, event)


def _reason(status: str) -> str:
    return {
        "waiting_for_stage11": "stage11_multisensory_extension_not_ready",
        "active_collecting_metrics": "long_term_metrics_are_still_collecting_or_canary_is_not_ready",
        "active_needs_check": "one_or_more_long_term_metrics_failed_the_audit_gate",
        "active_ready_for_stage13": "core_long_term_evaluation_metrics_are_clean",
    }.get(status, "unknown")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build XinYu Stage 12 long-term evaluation report.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--no-live-status", action="store_true")
    args = parser.parse_args(argv)
    live_status_data: dict[str, Any] | None = None
    live_status_error = ""
    if not args.no_live_status:
        live_status_data, live_status_error = _load_live_status(Path(args.root).resolve(), DEFAULT_CORE_URL)
    report = build_stage12_long_term_evaluation(
        args.root,
        live_status_data=live_status_data,
        live_status_error=live_status_error,
        load_live_status=False,
    )
    if args.write:
        report_path = write_stage12_long_term_evaluation_report(args.root, report, output=args.output)
        state_path = write_stage12_long_term_evaluation_state(args.root, report, report_path=report_path)
        trace_path = append_stage12_long_term_evaluation_trace(args.root, report)
        report["report_path"] = str(report_path)
        report["state_path"] = str(state_path)
        report["trace_path"] = str(trace_path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_stage12_long_term_evaluation(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
