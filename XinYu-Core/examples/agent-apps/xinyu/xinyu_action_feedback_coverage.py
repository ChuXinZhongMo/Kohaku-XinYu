from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_action_feedback_coverage_store import append_action_feedback_coverage_trace
from xinyu_action_feedback_coverage_store import latest_action_feedback_jsonl_row
from xinyu_action_feedback_coverage_store import read_action_feedback_coverage_json
from xinyu_action_feedback_coverage_store import read_action_feedback_coverage_text
from xinyu_action_feedback_coverage_store import write_action_feedback_coverage_text


STATE_REL = Path("memory/context/action_feedback_coverage_state.md")
TRACE_REL = Path("runtime/action_feedback_coverage_trace.jsonl")
REPORT_REL = Path("worklog/xinyu-action-feedback-coverage-latest.md")

ACTION_FEEDBACK_STATE_REL = Path("memory/context/action_feedback_state.md")
PROACTIVE_REQUEST_STATE_REL = Path("memory/context/proactive_request_state.md")
CODEX_PRESENCE_REL = Path("runtime/codex_presence_state.json")
SELF_ACTION_GATEWAY_STATE_REL = Path("memory/context/self_action_gateway_state.md")
SELF_ACTION_GATEWAY_TRACE_REL = Path("runtime/self_action_gateway/trace.jsonl")
PATCH_EXECUTOR_STATE_REL = Path("memory/context/self_action_patch_executor_state.md")
CODE_AWARENESS_STATE_REL = Path("memory/context/code_change_awareness_state.md")
RUNTIME_PRESENCE_STATE_REL = Path("memory/context/runtime_self_presence.md")

SURFACE_ORDER = (
    "qq",
    "desktop",
    "codex",
    "local_tool",
    "patch_executor",
    "code_probe",
    "runtime_probe",
)

NONE_VALUES = {"", "missing", "none", "unknown", "null"}
LIFECYCLE_VALUES = {
    "missing",
    "prepared",
    "started",
    "running",
    "succeeded",
    "failed",
    "dropped",
    "acked",
    "held",
    "partial",
    "needs_check",
}


def build_action_feedback_coverage_report(root: Path, *, generated_at: str | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    generated_at = generated_at or _now_iso()
    surfaces = {
        "qq": _qq_surface(root),
        "desktop": _desktop_surface(root),
        "codex": _codex_surface(root),
        "local_tool": _local_tool_surface(root),
        "patch_executor": _patch_executor_surface(root),
        "code_probe": _code_probe_surface(root),
        "runtime_probe": _runtime_probe_surface(root),
    }
    observed = [surface for surface in surfaces.values() if surface.get("observed")]
    non_qq = [surface for surface in observed if surface.get("surface") != "qq"]
    failures = [surface for surface in observed if surface.get("surface_status") == "needs_check"]
    future_effect_count = sum(1 for surface in observed if _present(surface.get("future_effect")))
    latest = _latest_surface(observed)
    status = _coverage_status(observed, non_qq, failures)

    report = {
        "ok": status in {"pass", "partial", "no_samples"},
        "status": status,
        "generated_at": generated_at,
        "root": str(root),
        "metrics": {
            "observed_surface_count": len(observed),
            "non_qq_surface_count": len(non_qq),
            "future_effect_count": future_effect_count,
            "failure_count": len(failures),
            "latest_feedback_signal": latest.get("feedback_signal", "none"),
            "latest_feedback_surface": latest.get("surface", "none"),
            "latest_lifecycle_status": latest.get("lifecycle_status", "missing"),
        },
        "surfaces": {name: _public_surface(surface) for name, surface in surfaces.items()},
        "privacy": {
            "raw_private_body_retained": False,
            "visible_reply_text_retained": False,
            "runtime_preview_text_retained": False,
            "state_contains_status_counts_refs_only": True,
            "stable_memory_write": "blocked",
        },
        "notes": _notes(status, observed, non_qq, failures),
    }
    return report


def read_action_feedback_coverage_state(root: Path) -> dict[str, str]:
    text = read_action_feedback_coverage_text(Path(root) / STATE_REL)
    if not text:
        return {"status": "missing", "observed_surface_count": "0", "non_qq_surface_count": "0"}
    return _parse_fields(text)


def render_action_feedback_coverage_report(report: dict[str, Any]) -> str:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    surfaces = report.get("surfaces") if isinstance(report.get("surfaces"), dict) else {}
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    lines = [
        "# XinYu Action Feedback Coverage",
        "",
        f"- generated_at: {report.get('generated_at', 'unknown')}",
        f"- status: {report.get('status', 'unknown')}",
        f"- result: {'pass' if report.get('ok') else 'needs_check'}",
        "- claim_boundary: action-result coverage only; does not claim consciousness",
        "",
        "## Metrics",
    ]
    for key in (
        "observed_surface_count",
        "non_qq_surface_count",
        "future_effect_count",
        "failure_count",
        "latest_feedback_signal",
        "latest_feedback_surface",
        "latest_lifecycle_status",
    ):
        lines.append(f"- {key}: {metrics.get(key, 'missing')}")
    lines.extend(["", "## Surfaces"])
    for name in SURFACE_ORDER:
        surface = surfaces.get(name) if isinstance(surfaces.get(name), dict) else {}
        lines.append(f"### {name}")
        for key in (
            "observed",
            "surface_status",
            "lifecycle_status",
            "feedback_signal",
            "action_result",
            "future_effect",
            "checked_at",
            "evidence_ref",
        ):
            lines.append(f"- {key}: {surface.get(key, 'missing')}")
    lines.extend(["", "## Privacy Boundary"])
    for key, value in privacy.items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Notes"])
    notes = report.get("notes") if isinstance(report.get("notes"), list) else []
    if notes:
        lines.extend(f"- {note}" for note in notes)
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def write_action_feedback_coverage(
    root: Path,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> dict[str, str]:
    root = Path(root).resolve()
    report_path = output if output is not None else root / REPORT_REL
    if not report_path.is_absolute():
        report_path = root / report_path
    write_action_feedback_coverage_text(report_path, render_action_feedback_coverage_report(report))
    _write_state(root, report, report_path=report_path)
    _append_trace(root, report)
    return {"report_path": str(report_path), "state_path": str(root / STATE_REL)}


def _qq_surface(root: Path) -> dict[str, Any]:
    fields = _parse_fields(read_action_feedback_coverage_text(root / ACTION_FEEDBACK_STATE_REL))
    signal = fields.get("feedback_signal", "missing")
    observed = _present(signal)
    result = fields.get("action_result", "missing")
    future_effect = fields.get("future_effect", "missing")
    surface_status = "missing"
    if observed:
        surface_status = "needs_check" if _result_failed(result) else "observed"
    return _surface(
        "qq",
        observed=observed,
        surface_status=surface_status,
        feedback_signal=signal if observed else "missing",
        action_result=result,
        future_effect=future_effect,
        checked_at=fields.get("checked_at", "missing"),
        evidence_ref=fields.get("event_id", "none"),
    )


def _desktop_surface(root: Path) -> dict[str, Any]:
    fields = _parse_fields(read_action_feedback_coverage_text(root / PROACTIVE_REQUEST_STATE_REL))
    state_status = fields.get("status", "missing")
    answer_state = fields.get("request_answer_state", "missing")
    last_ack = fields.get("last_ack_status", "missing")
    adapter_error = fields.get("adapter_error", "missing")
    requested_action = fields.get("requested_action", "missing")
    observed = any(_present(value) for value in (state_status, answer_state, last_ack, adapter_error, requested_action))
    signal = "missing"
    result = "missing"
    future_effect = "missing"
    surface_status = "missing"

    if _present(adapter_error):
        signal = "desktop_qq_enqueue_failed"
        result = "failed"
        future_effect = "check_desktop_or_qq_delivery_before_future_request"
        surface_status = "needs_check"
    elif answer_state in {"read_locally", "read_local", "read"}:
        signal = "desktop_read_locally"
        result = "owner_read_locally"
        future_effect = "prefer_desktop_thread_followup_without_reasking_same_prompt"
        surface_status = "observed"
    elif answer_state in {"dismiss", "dismissed"}:
        signal = "desktop_dismissed"
        result = "owner_dismissed"
        future_effect = "lower_same_request_priority_until_new_evidence"
        surface_status = "observed"
    elif answer_state in {"reply", "replied", "answered", "owner_replied"}:
        signal = "desktop_owner_replied"
        result = "owner_replied"
        future_effect = "route_owner_reply_back_to_source_thread"
        surface_status = "observed"
    elif answer_state in {"approve_qq", "approved_qq", "approved"}:
        signal = "desktop_approved_qq"
        result = "owner_approved_qq"
        future_effect = "allow_one_bounded_qq_enqueue_if_other_gates_pass"
        surface_status = "observed"
    elif last_ack in {"acked", "sent", "delivered", "ok", "success"}:
        signal = "desktop_request_ack"
        result = "delivered"
        future_effect = "keep_desktop_request_route_available"
        surface_status = "observed"
    elif last_ack == "dry_run" or state_status == "dry_run":
        signal = "desktop_dry_run_observed"
        result = "held_dry_run"
        future_effect = "keep_owner_request_review_gated_until_real_ack"
        surface_status = "observed"
    elif observed:
        signal = "desktop_request_state_seen"
        result = state_status
        future_effect = "keep_desktop_request_state_auditable"
        surface_status = "observed"

    return _surface(
        "desktop",
        observed=observed,
        surface_status=surface_status,
        feedback_signal=signal,
        action_result=result,
        future_effect=future_effect,
        checked_at=fields.get("checked_at") or fields.get("created_at", "missing"),
        evidence_ref=_content_ref(fields.get("request_id") or fields.get("thread_id") or ""),
    )


def _codex_surface(root: Path) -> dict[str, Any]:
    data = _read_json(root / CODEX_PRESENCE_REL)
    status = _safe_str(data.get("status"), "missing")
    observed = _present(status)
    exit_code = _safe_str(data.get("exit_code"), "")
    timed_out = data.get("timed_out") is True or _safe_str(data.get("timed_out")).lower() == "true"
    signal = "missing"
    result = "missing"
    future_effect = "missing"
    surface_status = "missing"
    if timed_out:
        signal = "codex_delegate_timeout"
        result = "timeout"
        future_effect = "prefer_smaller_codex_tasks_or_manual_check"
        surface_status = "needs_check"
    elif status in {"failed", "error", "cancelled"} or (_present(exit_code) and exit_code != "0"):
        signal = "codex_delegate_failed"
        result = "failed"
        future_effect = "inspect_codex_report_before_redelegating"
        surface_status = "needs_check"
    elif status in {"finished", "complete", "completed"}:
        signal = "codex_delegate_finished"
        result = "succeeded"
        future_effect = "allow_codex_delegation_pattern_when_bounded"
        surface_status = "observed"
    elif observed:
        signal = "codex_delegate_in_progress"
        result = status
        future_effect = "wait_for_delegate_result_before_claiming_completion"
        surface_status = "partial"
    return _surface(
        "codex",
        observed=observed,
        surface_status=surface_status,
        feedback_signal=signal,
        action_result=result,
        future_effect=future_effect,
        checked_at=_safe_str(data.get("updated_at"), "missing"),
        evidence_ref=_content_ref(data.get("job_id") or data.get("report_label") or ""),
    )


def _local_tool_surface(root: Path) -> dict[str, Any]:
    executed = _latest_jsonl_row(root / SELF_ACTION_GATEWAY_TRACE_REL, lambda row: row.get("event_kind") == "self_action_executed")
    if executed:
        result = _safe_str(executed.get("result"), "missing")
        failed = result in {"failed", "error"} or _present(executed.get("error_code"))
        return _surface(
            "local_tool",
            observed=True,
            surface_status="needs_check" if failed else "observed",
            feedback_signal="local_tool_probe_failed" if failed else "local_tool_probe_succeeded",
            action_result=result,
            future_effect=(
                "prefer_diagnostic_or_owner_review_before_repeating_tool_probe"
                if failed
                else "keep_low_risk_probe_available_for_bounded_checks"
            ),
            checked_at=_safe_str(executed.get("checked_at"), "missing"),
            evidence_ref=_content_ref(executed.get("action_id") or executed.get("report_ref") or ""),
        )

    fields = _parse_fields(read_action_feedback_coverage_text(root / SELF_ACTION_GATEWAY_STATE_REL))
    execution_result = fields.get("execution_result", "missing")
    observed = _present(execution_result)
    signal = "self_action_handoff_created" if execution_result == "handoff_created" else "self_action_state_seen"
    future_effect = "wait_owner_or_codex_before_execute_patch" if execution_result == "handoff_created" else "keep_gateway_result_auditable"
    return _surface(
        "local_tool",
        observed=observed,
        surface_status="observed" if observed else "missing",
        feedback_signal=signal if observed else "missing",
        action_result=execution_result,
        future_effect=future_effect if observed else "missing",
        checked_at=fields.get("checked_at", "missing"),
        evidence_ref=_content_ref(fields.get("queue_id") or fields.get("latest_executed_queue_id") or ""),
    )


def _patch_executor_surface(root: Path) -> dict[str, Any]:
    fields = _parse_fields(read_action_feedback_coverage_text(root / PATCH_EXECUTOR_STATE_REL))
    status = fields.get("status", "missing")
    codex_status = fields.get("codex_status", "missing")
    observed = _present(status)
    failed = status in {"failed", "error"} or codex_status in {"failed", "error", "timeout"}
    if failed:
        signal = "patch_codex_failed" if _present(codex_status) else "patch_task_failed"
        result = codex_status if _present(codex_status) else status
        future_effect = "inspect_patch_task_or_codex_report_before_retry"
        surface_status = "needs_check"
    elif codex_status in {"finished", "complete", "completed"}:
        signal = "patch_codex_finished"
        result = "succeeded"
        future_effect = "allow_patch_result_review_before_source_claim"
        surface_status = "observed"
    elif status == "prepared":
        signal = "patch_task_prepared"
        result = "prepared"
        future_effect = "task_available_for_codex_or_owner_review"
        surface_status = "observed"
    elif observed:
        signal = "patch_executor_state_seen"
        result = status
        future_effect = "keep_patch_executor_state_auditable"
        surface_status = "partial"
    else:
        signal = "missing"
        result = "missing"
        future_effect = "missing"
        surface_status = "missing"
    return _surface(
        "patch_executor",
        observed=observed,
        surface_status=surface_status,
        feedback_signal=signal,
        action_result=result,
        future_effect=future_effect,
        checked_at=fields.get("checked_at", "missing"),
        evidence_ref=_content_ref(fields.get("task_id") or fields.get("queue_id") or fields.get("task_path") or ""),
    )


def _code_probe_surface(root: Path) -> dict[str, Any]:
    fields = _parse_fields(read_action_feedback_coverage_text(root / CODE_AWARENESS_STATE_REL))
    status = fields.get("status", "missing")
    observed = _present(status)
    source_changed = _bool_field(fields, "source_changed")
    restart_required = any(
        _bool_field(fields, key)
        for key in ("bridge_restart_required", "runtime_restart_required", "gateway_restart_may_be_needed")
    )
    if restart_required:
        signal = "code_probe_restart_required"
        result = "restart_required"
        future_effect = "restart_or_verify_loaded_source_before_claiming_change"
        surface_status = "needs_check"
    elif source_changed:
        signal = "code_probe_source_changed"
        result = "source_changed"
        future_effect = "verify_restart_need_before_next_runtime_claim"
        surface_status = "observed"
    elif observed:
        signal = "code_probe_clean"
        result = status
        future_effect = "confirm_loaded_source_consistency_before_next_claim"
        surface_status = "observed"
    else:
        signal = "missing"
        result = "missing"
        future_effect = "missing"
        surface_status = "missing"
    return _surface(
        "code_probe",
        observed=observed,
        surface_status=surface_status,
        feedback_signal=signal,
        action_result=result,
        future_effect=future_effect,
        checked_at=fields.get("updated_at", "missing"),
        evidence_ref=_content_ref(fields.get("current_project_digest") or ""),
    )


def _runtime_probe_surface(root: Path) -> dict[str, Any]:
    fields = _parse_fields(read_action_feedback_coverage_text(root / RUNTIME_PRESENCE_STATE_REL))
    bridge_process = fields.get("bridge_process", "missing")
    turn_state = fields.get("current_turn_state", "missing")
    last_turn_status = fields.get("last_turn_status", "missing")
    observed = any(_present(value) for value in (bridge_process, turn_state, last_turn_status))
    unhealthy = bridge_process not in {"missing", "running"} or last_turn_status in {"failed", "error", "timeout"}
    if unhealthy:
        signal = "runtime_probe_error"
        result = "unhealthy"
        future_effect = "avoid_outward_action_until_runtime_health_recovers"
        surface_status = "needs_check"
    elif turn_state in {"running", "processing"}:
        signal = "runtime_probe_turn_active"
        result = "turn_active"
        future_effect = "avoid_duplicate_action_while_current_turn_active"
        surface_status = "observed"
    elif observed:
        signal = "runtime_probe_ok"
        result = "running"
        future_effect = "confirm_runtime_alive_for_next_action"
        surface_status = "observed"
    else:
        signal = "missing"
        result = "missing"
        future_effect = "missing"
        surface_status = "missing"
    return _surface(
        "runtime_probe",
        observed=observed,
        surface_status=surface_status,
        feedback_signal=signal,
        action_result=result,
        future_effect=future_effect,
        checked_at=fields.get("last_turn_at") or fields.get("updated_at", "missing"),
        evidence_ref=_content_ref(fields.get("last_turn_id") or fields.get("current_turn_id") or ""),
        lifecycle_status=(
            "failed"
            if unhealthy
            else "running"
            if turn_state in {"running", "processing"}
            else "succeeded"
            if observed
            else "missing"
        ),
    )


def _write_state(root: Path, report: dict[str, Any], *, report_path: Path) -> None:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    surfaces = report.get("surfaces") if isinstance(report.get("surfaces"), dict) else {}

    def surface_status(name: str) -> str:
        surface = surfaces.get(name) if isinstance(surfaces.get(name), dict) else {}
        return _safe_str(surface.get("surface_status"), "missing")

    def surface_lifecycle(name: str) -> str:
        surface = surfaces.get(name) if isinstance(surfaces.get(name), dict) else {}
        return _safe_str(surface.get("lifecycle_status"), "missing")

    text = f"""---
title: Action Feedback Coverage State
memory_type: action_feedback_coverage_state
time_scope: rolling_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_action_feedback_coverage
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, action-result, feedback, coverage]
---

# Action Feedback Coverage State

## Current Coverage
- status: {report.get('status', 'unknown')}
- checked_at: {report.get('generated_at', 'unknown')}
- observed_surface_count: {metrics.get('observed_surface_count', 0)}
- non_qq_surface_count: {metrics.get('non_qq_surface_count', 0)}
- qq_feedback_status: {surface_status('qq')}
- desktop_feedback_status: {surface_status('desktop')}
- codex_feedback_status: {surface_status('codex')}
- local_tool_feedback_status: {surface_status('local_tool')}
- patch_executor_feedback_status: {surface_status('patch_executor')}
- code_probe_status: {surface_status('code_probe')}
- runtime_probe_status: {surface_status('runtime_probe')}
- future_effect_count: {metrics.get('future_effect_count', 0)}
- failure_count: {metrics.get('failure_count', 0)}
- latest_feedback_signal: {metrics.get('latest_feedback_signal', 'none')}
- latest_feedback_surface: {metrics.get('latest_feedback_surface', 'none')}
- latest_lifecycle_status: {metrics.get('latest_lifecycle_status', 'missing')}
- qq_lifecycle_status: {surface_lifecycle('qq')}
- desktop_lifecycle_status: {surface_lifecycle('desktop')}
- codex_lifecycle_status: {surface_lifecycle('codex')}
- local_tool_lifecycle_status: {surface_lifecycle('local_tool')}
- patch_executor_lifecycle_status: {surface_lifecycle('patch_executor')}
- code_probe_lifecycle_status: {surface_lifecycle('code_probe')}
- runtime_probe_lifecycle_status: {surface_lifecycle('runtime_probe')}

## Boundaries
- report_path: {report_path.as_posix()}
- raw_private_body_retained: false
- visible_reply_text_retained: false
- runtime_preview_text_retained: false
- stable_memory_write: blocked
"""
    write_action_feedback_coverage_text(root / STATE_REL, text)


def _append_trace(root: Path, report: dict[str, Any]) -> None:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    surfaces = report.get("surfaces") if isinstance(report.get("surfaces"), dict) else {}
    row = {
        "generated_at": report.get("generated_at", ""),
        "status": report.get("status", ""),
        "ok": bool(report.get("ok")),
        "observed_surface_count": metrics.get("observed_surface_count", 0),
        "non_qq_surface_count": metrics.get("non_qq_surface_count", 0),
        "future_effect_count": metrics.get("future_effect_count", 0),
        "failure_count": metrics.get("failure_count", 0),
        "latest_feedback_signal": metrics.get("latest_feedback_signal", "none"),
        "latest_feedback_surface": metrics.get("latest_feedback_surface", "none"),
        "latest_lifecycle_status": metrics.get("latest_lifecycle_status", "missing"),
        "surface_statuses": {
            name: (surfaces.get(name) or {}).get("surface_status", "missing")
            for name in SURFACE_ORDER
        },
        "surface_lifecycles": {
            name: (surfaces.get(name) or {}).get("lifecycle_status", "missing")
            for name in SURFACE_ORDER
        },
        "raw_private_body_retained": False,
        "visible_reply_text_retained": False,
        "runtime_preview_text_retained": False,
    }
    append_action_feedback_coverage_trace(root / TRACE_REL, row)


def _surface(
    surface: str,
    *,
    observed: bool,
    surface_status: str,
    feedback_signal: str,
    action_result: str,
    future_effect: str,
    checked_at: str,
    evidence_ref: str,
    lifecycle_status: str | None = None,
) -> dict[str, Any]:
    lifecycle = _normalize_lifecycle(
        lifecycle_status
        if lifecycle_status is not None
        else _lifecycle_from_result(feedback_signal, action_result, surface_status)
    )
    return {
        "surface": surface,
        "observed": bool(observed),
        "surface_status": surface_status,
        "lifecycle_status": lifecycle,
        "feedback_signal": _one_line(feedback_signal),
        "action_result": _one_line(action_result),
        "future_effect": _one_line(future_effect),
        "checked_at": _one_line(checked_at),
        "evidence_ref": _one_line(evidence_ref),
    }


def _public_surface(surface: dict[str, Any]) -> dict[str, Any]:
    return {
        "surface": _safe_str(surface.get("surface"), "unknown"),
        "observed": bool(surface.get("observed")),
        "surface_status": _safe_str(surface.get("surface_status"), "missing"),
        "lifecycle_status": _normalize_lifecycle(surface.get("lifecycle_status")),
        "feedback_signal": _safe_str(surface.get("feedback_signal"), "missing"),
        "action_result": _safe_str(surface.get("action_result"), "missing"),
        "future_effect": _safe_str(surface.get("future_effect"), "missing"),
        "checked_at": _safe_str(surface.get("checked_at"), "missing"),
        "evidence_ref": _safe_str(surface.get("evidence_ref"), "none"),
    }


def _coverage_status(observed: list[dict[str, Any]], non_qq: list[dict[str, Any]], failures: list[dict[str, Any]]) -> str:
    if not observed:
        return "no_samples"
    if failures:
        return "needs_check"
    if non_qq and len(observed) >= 2:
        return "pass"
    return "partial"


def _latest_surface(surfaces: list[dict[str, Any]]) -> dict[str, Any]:
    if not surfaces:
        return {}
    dated: list[tuple[datetime, dict[str, Any]]] = []
    for surface in surfaces:
        parsed = _parse_timestamp(surface.get("checked_at"))
        if parsed is not None:
            dated.append((parsed, surface))
    if dated:
        dated.sort(key=lambda item: item[0])
        return dated[-1][1]
    return surfaces[-1]


def _notes(
    status: str,
    observed: list[dict[str, Any]],
    non_qq: list[dict[str, Any]],
    failures: list[dict[str, Any]],
) -> list[str]:
    notes: list[str] = []
    if not observed:
        notes.append("no_action_feedback_surfaces_observed")
    if observed and not non_qq:
        notes.append("only_qq_feedback_surface_observed")
    if non_qq:
        notes.append("non_qq_feedback_surface_observed")
    for surface in failures[:4]:
        notes.append(f"needs_check:{surface.get('surface')}:{surface.get('feedback_signal')}")
    if status == "pass":
        notes.append("multi_surface_feedback_coverage_clean")
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


def _read_json(path: Path) -> dict[str, Any]:
    return read_action_feedback_coverage_json(path)


def _latest_jsonl_row(path: Path, predicate: Any, *, max_lines: int = 400) -> dict[str, Any]:
    return latest_action_feedback_jsonl_row(path, predicate, max_lines=max_lines)


def _parse_timestamp(value: Any) -> datetime | None:
    text = _safe_str(value).strip().replace("Z", "+00:00")
    if not text or text in NONE_VALUES:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _content_ref(value: Any) -> str:
    text = _safe_str(value).strip()
    if not text:
        return "none"
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _normalize_lifecycle(value: Any) -> str:
    text = _safe_str(value, "missing").strip().lower()
    return text if text in LIFECYCLE_VALUES else "partial"


def _lifecycle_from_result(signal: Any, result: Any, surface_status: Any) -> str:
    status_text = _safe_str(surface_status).strip().lower()
    signal_text = _safe_str(signal).strip().lower()
    result_text = _safe_str(result).strip().lower()
    combined = f"{signal_text} {result_text}"
    if status_text == "missing" or (signal_text in NONE_VALUES and result_text in NONE_VALUES):
        return "missing"
    if "restart_required" in combined:
        return "needs_check"
    if any(marker in combined for marker in ("dry_run", "hold", "held")):
        return "held"
    if any(marker in combined for marker in ("stale", "drop", "dropped", "dismiss", "retract")):
        return "dropped"
    if status_text == "needs_check" or any(
        marker in combined for marker in ("failed", "failure", "error", "timeout", "unhealthy")
    ):
        return "failed"
    if any(marker in combined for marker in ("ack", "delivered", "sent", "read", "approved", "replied")):
        return "acked"
    if any(marker in combined for marker in ("prepared", "handoff_created", "queued")):
        return "prepared"
    if any(marker in combined for marker in ("started", "dispatch_start")):
        return "started"
    if any(marker in combined for marker in ("running", "processing", "in_progress", "turn_active")):
        return "running"
    if any(marker in combined for marker in ("succeeded", "success", "finished", "complete", "clean", "source_changed")):
        return "succeeded"
    if status_text == "partial":
        return "partial"
    return "partial"


def _result_failed(value: Any) -> bool:
    text = _safe_str(value).lower()
    return any(marker in text for marker in ("fail", "error", "timeout", "not_updated", "restart_required"))


def _bool_field(fields: dict[str, str], key: str) -> bool:
    return _safe_str(fields.get(key)).strip().lower() in {"true", "1", "yes"}


def _present(value: Any) -> bool:
    return _safe_str(value).strip().lower() not in NONE_VALUES


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _one_line(value: Any, limit: int = 160) -> str:
    text = " ".join(_safe_str(value).split())
    if not text:
        return "none"
    return text[: max(1, int(limit))]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build XinYu multi-action feedback coverage.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_action_feedback_coverage_report(args.root)
    if args.write:
        report.update(write_action_feedback_coverage(args.root, report, output=args.output))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_action_feedback_coverage_report(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
