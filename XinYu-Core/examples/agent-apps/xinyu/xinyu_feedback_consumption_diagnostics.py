from __future__ import annotations


__all__ = (
    "STATE_REL",
    "INTENTION_TRACE_REL",
    "INTENTION_STATE_REL",
    "REPORT_REL",
    "TRACE_REL",
)

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_feedback_consumption_diagnostics_store import append_feedback_consumption_trace_event
from xinyu_feedback_consumption_diagnostics_store import read_feedback_consumption_jsonl_tail
from xinyu_feedback_consumption_diagnostics_store import read_feedback_consumption_state_text
from xinyu_feedback_consumption_diagnostics_store import write_feedback_consumption_report_text
from xinyu_feedback_consumption_diagnostics_store import write_feedback_consumption_state_text
from xinyu_feedback_consumption_diagnostics_store import INTENTION_STATE_REL, INTENTION_TRACE_REL, REPORT_REL, STATE_REL, TRACE_REL




DEFAULT_TRACE_LIMIT = 200
PASS_RATE_PCT = 80.0
MIN_STAGE7_CLOSURE_SAMPLES = 3
NONE_VALUES = {"", "missing", "none", "unknown", "null", "no_feedback"}
AUDIT_FIELDS = (
    "feedback_consumption_status",
    "feedback_consumed_sources",
    "feedback_consumed_biases",
    "feedback_consumed_future_effect",
)


def build_feedback_consumption_diagnostics(
    root: Path,
    *,
    trace_limit: int = DEFAULT_TRACE_LIMIT,
    generated_at: str | None = None,
    include_current_state: bool = True,
    include_latest_decision: bool = True,
    min_stage7_closure_samples: int = MIN_STAGE7_CLOSURE_SAMPLES,
) -> dict[str, Any]:
    root = Path(root).resolve()
    generated_at = generated_at or _now_iso()
    rows = read_feedback_consumption_jsonl_tail(root / INTENTION_TRACE_REL, max_lines=max(1, int(trace_limit)))
    samples = [_sample_from_row(row, source="trace") for row in rows]
    samples = [sample for sample in samples if sample]

    if include_current_state:
        state_sample = _sample_from_state(root)
        if state_sample and not _same_latest_sample(samples[-1] if samples else {}, state_sample):
            samples.append(state_sample)
    if include_latest_decision:
        decision_sample = _sample_from_latest_decision(root)
        if decision_sample and not _same_latest_sample(samples[-1] if samples else {}, decision_sample):
            samples.append(decision_sample)

    auditable_samples = [sample for sample in samples if sample.get("status") != "legacy_uninstrumented"]
    consumed_count = sum(1 for sample in auditable_samples if sample.get("status") == "consumed")
    partial_count = sum(1 for sample in auditable_samples if sample.get("status") == "partial")
    missing_count = sum(1 for sample in auditable_samples if sample.get("status") in {"missing", "no_feedback"})
    required_count = len(auditable_samples)
    legacy_count = len(samples) - required_count
    rate = round((consumed_count / required_count) * 100, 1) if required_count else 0.0
    latest = auditable_samples[-1] if auditable_samples else (samples[-1] if samples else {})
    latest_status = str(latest.get("status", "none"))
    consumed_streak = _status_streak(auditable_samples, {"consumed"})
    missing_streak = _status_streak(auditable_samples, {"partial", "missing", "no_feedback"})

    if required_count <= 0:
        status = "no_samples"
    elif latest_status != "consumed":
        status = "needs_check"
    elif rate < PASS_RATE_PCT:
        status = "needs_check"
    else:
        status = "pass"

    min_samples = max(1, int(min_stage7_closure_samples))
    metrics = {
        "sample_count": len(samples),
        "feedback_source_count": len(samples),
        "feedback_required_count": required_count,
        "legacy_uninstrumented_count": legacy_count,
        "consumed_count": consumed_count,
        "partial_count": partial_count,
        "missing_count": missing_count,
        "consumption_rate_pct": rate,
        "pass_rate_pct": PASS_RATE_PCT,
        "consumed_streak": consumed_streak,
        "missing_streak": missing_streak,
        "stage7_closure_min_samples": min_samples,
    }
    stage7_closure = _stage7_closure(status, metrics, latest_status)
    report = {
        "ok": status in {"pass", "no_samples"},
        "status": status,
        "generated_at": generated_at,
        "root": str(root),
        "trace_limit": max(1, int(trace_limit)),
        "include_current_state": bool(include_current_state),
        "include_latest_decision": bool(include_latest_decision),
        "metrics": metrics,
        "stage7_feedback_closure": stage7_closure,
        "latest_sample": _public_sample(latest),
        "privacy": {
            "raw_owner_text_in_report": False,
            "visible_reply_text_in_report": False,
            "state_contains_status_counts_refs_only": True,
            "stable_memory_write": "blocked",
            "consciousness_claim": False,
        },
        "notes": _notes(status, metrics, latest_status, stage7_closure),
    }
    return report


def render_feedback_consumption_diagnostics(report: dict[str, Any]) -> str:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    closure = (
        report.get("stage7_feedback_closure")
        if isinstance(report.get("stage7_feedback_closure"), dict)
        else {}
    )
    latest = report.get("latest_sample") if isinstance(report.get("latest_sample"), dict) else {}
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    lines = [
        "# XinYu Feedback Consumption Diagnostics",
        "",
        f"- generated_at: {report.get('generated_at', 'unknown')}",
        f"- status: {report.get('status', 'unknown')}",
        f"- result: {'pass' if report.get('ok') else 'needs_check'}",
        f"- trace_limit: {report.get('trace_limit', 'unknown')}",
        "- claim_boundary: rolling feedback-consumption audit only; does not claim consciousness",
        "",
        "## Metrics",
    ]
    for key in (
        "sample_count",
        "feedback_source_count",
        "feedback_required_count",
        "legacy_uninstrumented_count",
        "consumed_count",
        "partial_count",
        "missing_count",
        "consumption_rate_pct",
        "pass_rate_pct",
        "consumed_streak",
        "missing_streak",
        "stage7_closure_min_samples",
    ):
        lines.append(f"- {key}: {metrics.get(key, 'missing')}")
    lines.extend(["", "## Stage 7 Closure Gate"])
    for key in (
        "status",
        "ready_for_stage8",
        "reason",
        "required_samples",
        "auditable_samples",
        "consumed_streak",
        "consumption_rate_pct",
        "next_step",
    ):
        value = closure.get(key, "missing")
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else value}")
    lines.extend(["", "## Latest Sample"])
    for key in (
        "source",
        "checked_at",
        "ecology_id",
        "status",
        "sources",
        "biases",
        "future_effect",
    ):
        lines.append(f"- {key}: {latest.get(key, 'none')}")
    lines.extend(["", "## Privacy Boundary"])
    for key, value in privacy.items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Notes"])
    notes = report.get("notes") if isinstance(report.get("notes"), list) else []
    lines.extend(f"- {note}" for note in notes) if notes else lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def write_feedback_consumption_diagnostics(
    root: Path,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> dict[str, str]:
    root = Path(root).resolve()
    report_path = write_feedback_consumption_report_text(
        root,
        render_feedback_consumption_diagnostics(report),
        output=output,
    )
    _write_state(root, report, report_path=report_path)
    _append_trace(root, report)
    return {"report_path": str(report_path), "state_path": str(root / STATE_REL)}


def _write_state(root: Path, report: dict[str, Any], *, report_path: Path) -> None:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    closure = (
        report.get("stage7_feedback_closure")
        if isinstance(report.get("stage7_feedback_closure"), dict)
        else {}
    )
    latest = report.get("latest_sample") if isinstance(report.get("latest_sample"), dict) else {}
    text = f"""---
title: Feedback Consumption Diagnostics State
memory_type: feedback_consumption_diagnostics_state
time_scope: rolling_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_feedback_consumption_diagnostics
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, feedback, diagnostics, closed-loop]
---

# Feedback Consumption Diagnostics State

## Current Window
- status: {report.get('status', 'unknown')}
- checked_at: {report.get('generated_at', 'unknown')}
- sample_count: {metrics.get('sample_count', 0)}
- feedback_source_count: {metrics.get('feedback_source_count', 0)}
- feedback_required_count: {metrics.get('feedback_required_count', 0)}
- legacy_uninstrumented_count: {metrics.get('legacy_uninstrumented_count', 0)}
- consumed_count: {metrics.get('consumed_count', 0)}
- partial_count: {metrics.get('partial_count', 0)}
- missing_count: {metrics.get('missing_count', 0)}
- consumption_rate_pct: {metrics.get('consumption_rate_pct', 0.0)}
- pass_rate_pct: {metrics.get('pass_rate_pct', PASS_RATE_PCT)}
- consumed_streak: {metrics.get('consumed_streak', 0)}
- missing_streak: {metrics.get('missing_streak', 0)}
- stage7_closure_min_samples: {metrics.get('stage7_closure_min_samples', MIN_STAGE7_CLOSURE_SAMPLES)}

## Stage 7 Closure Gate
- stage7_feedback_closure_status: {closure.get('status', 'missing')}
- stage7_ready_for_stage8: {str(closure.get('ready_for_stage8', False)).lower()}
- stage7_closure_reason: {closure.get('reason', 'missing')}
- stage7_required_samples: {closure.get('required_samples', MIN_STAGE7_CLOSURE_SAMPLES)}
- stage7_auditable_samples: {closure.get('auditable_samples', 0)}
- stage7_consumed_streak: {closure.get('consumed_streak', 0)}
- stage7_consumption_rate_pct: {closure.get('consumption_rate_pct', 0.0)}
- stage7_next_step: {closure.get('next_step', 'missing')}

## Latest Sample
- latest_source: {latest.get('source', 'none')}
- latest_checked_at: {latest.get('checked_at', 'none')}
- latest_ecology_id: {latest.get('ecology_id', 'none')}
- latest_status: {latest.get('status', 'none')}
- latest_sources: {latest.get('sources', 'none')}
- latest_biases: {latest.get('biases', 'none')}
- latest_future_effect: {latest.get('future_effect', 'none')}

## Boundaries
- report_path: {report_path.as_posix()}
- raw_owner_text_in_state: false
- visible_reply_text_in_state: false
- state_contains_status_counts_refs_only: true
- stable_memory_write: blocked
- consciousness_claim: false
"""
    write_feedback_consumption_state_text(root, text)


def _append_trace(root: Path, report: dict[str, Any]) -> None:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    closure = (
        report.get("stage7_feedback_closure")
        if isinstance(report.get("stage7_feedback_closure"), dict)
        else {}
    )
    latest = report.get("latest_sample") if isinstance(report.get("latest_sample"), dict) else {}
    row = {
        "generated_at": report.get("generated_at", ""),
        "status": report.get("status", ""),
        "ok": bool(report.get("ok")),
        "sample_count": metrics.get("sample_count", 0),
        "feedback_required_count": metrics.get("feedback_required_count", 0),
        "legacy_uninstrumented_count": metrics.get("legacy_uninstrumented_count", 0),
        "consumed_count": metrics.get("consumed_count", 0),
        "partial_count": metrics.get("partial_count", 0),
        "missing_count": metrics.get("missing_count", 0),
        "consumption_rate_pct": metrics.get("consumption_rate_pct", 0.0),
        "latest_status": latest.get("status", "none"),
        "latest_sources": latest.get("sources", "none"),
        "latest_biases": latest.get("biases", "none"),
        "latest_future_effect": latest.get("future_effect", "none"),
        "consumed_streak": metrics.get("consumed_streak", 0),
        "missing_streak": metrics.get("missing_streak", 0),
        "stage7_feedback_closure_status": closure.get("status", "missing"),
        "stage7_ready_for_stage8": bool(closure.get("ready_for_stage8")),
        "stage7_closure_reason": closure.get("reason", "missing"),
        "stage7_required_samples": closure.get("required_samples", MIN_STAGE7_CLOSURE_SAMPLES),
        "stage7_next_step": closure.get("next_step", "missing"),
        "raw_owner_text_in_trace": False,
        "visible_reply_text_in_trace": False,
        "consciousness_claim": False,
    }
    append_feedback_consumption_trace_event(root, row)


def _sample_from_state(root: Path) -> dict[str, str]:
    fields = _parse_fields(read_feedback_consumption_state_text(root))
    if not fields:
        return {}
    return _sample_from_row(fields, source="current_state")


def _sample_from_latest_decision(root: Path) -> dict[str, str]:
    try:
        from xinyu_decision_chain_latest import build_decision_chain_latest_report

        report = build_decision_chain_latest_report(root)
    except Exception:
        return {}
    chain = report.get("decision_chain") if isinstance(report.get("decision_chain"), dict) else {}
    if not chain:
        return {}
    row = {
        "checked_at": report.get("generated_at", "none"),
        "ecology_id": "decision_chain_latest",
        "feedback_consumption_status": chain.get("feedback_consumption_status", "missing"),
        "feedback_consumed_sources": chain.get("feedback_consumed_sources", "none"),
        "feedback_consumed_biases": chain.get("feedback_consumed_biases", "none"),
        "feedback_consumed_future_effect": chain.get("feedback_consumed_future_effect", "none"),
    }
    return _sample_from_row(row, source="latest_decision_chain")


def _sample_from_row(row: dict[str, Any], *, source: str) -> dict[str, str]:
    if not isinstance(row, dict):
        return {}
    has_audit_fields = any(field in row for field in AUDIT_FIELDS)
    sources = _public_value(row.get("feedback_consumed_sources"))
    if not _present(sources):
        sources = _derived_sources(row)
    if not _present(sources):
        return {}

    status = _public_value(row.get("feedback_consumption_status"))
    biases = _public_value(row.get("feedback_consumed_biases"), default="none")
    future_effect = _public_value(row.get("feedback_consumed_future_effect"), default="none")
    if not has_audit_fields:
        biases = _derived_biases(row)
        future_effect = _derived_future_effects(row)
        status = "consumed" if _present(biases) and _present(future_effect) else "legacy_uninstrumented"
    elif not _present(status):
        status = "missing"
    elif status == "no_feedback":
        status = "missing"

    return {
        "source": source,
        "checked_at": _public_value(row.get("checked_at"), default="none"),
        "ecology_id": _public_value(row.get("ecology_id"), default="none"),
        "status": status,
        "sources": sources,
        "biases": biases,
        "future_effect": future_effect,
    }


def _derived_sources(row: dict[str, Any]) -> str:
    parts: list[str] = []
    _append_source(parts, "action_feedback", row.get("action_feedback_signal"))
    coverage_signal = _public_value(row.get("action_feedback_coverage_signal"), default="none")
    if _present(coverage_signal):
        lifecycle = _public_value(row.get("action_feedback_coverage_lifecycle"), default="none")
        suffix = f"/{lifecycle}" if _present(lifecycle) else ""
        parts.append(f"action_feedback_coverage:{coverage_signal}{suffix}")
    _append_source(parts, "owner_feedback_effect", row.get("owner_feedback_effect_signal"))
    _append_source(parts, "owner_response_feedback", row.get("owner_response_feedback_signal"))
    _append_source(parts, "perception_gap", row.get("perception_gap_signal"))
    return _join_parts(parts)


def _derived_biases(row: dict[str, Any]) -> str:
    parts: list[str] = []
    _append_labeled_value(parts, "action_feedback_bias", row.get("action_feedback_bias"))
    _append_labeled_value(parts, "action_feedback_coverage_bias", row.get("action_feedback_coverage_bias"))
    _append_labeled_value(parts, "owner_feedback_effect_bias", row.get("owner_feedback_effect_bias"))
    _append_labeled_value(parts, "owner_feedback_expression_bias", row.get("owner_feedback_expression_bias"))
    _append_labeled_value(parts, "owner_response_feedback_bias", row.get("owner_response_feedback_bias"))
    _append_labeled_value(parts, "owner_response_strategy_bias", row.get("owner_response_strategy_bias"))
    _append_labeled_value(parts, "perception_gap_bias", row.get("perception_gap_bias"))
    return _join_parts(parts)


def _derived_future_effects(row: dict[str, Any]) -> str:
    parts: list[str] = []
    action_signal = _public_value(row.get("action_feedback_signal"), default="none")
    if action_signal in {"qq_visible_reply_ack", "qq_outbox_delivery_ack"}:
        parts.append("action_feedback_future:confirm_visible_reply_transport_for_next_turn")
    elif action_signal == "qq_stale_reply_drop":
        parts.append("action_feedback_future:prefer_latest_owner_input_before_claiming_drop")
    elif action_signal == "qq_visible_reply_send_failed":
        parts.append("action_feedback_future:raise_visible_reply_transport_risk")

    coverage_signal = _public_value(row.get("action_feedback_coverage_signal"), default="none")
    coverage_lifecycle = _public_value(row.get("action_feedback_coverage_lifecycle"), default="none")
    if coverage_signal in {
        "runtime_probe_turn_active",
        "runtime_probe_ok",
        "code_probe_clean_source_claim",
        "local_tool_probe_succeeded",
        "codex_delegate_finished",
        "patch_task_prepared",
    }:
        suffix = f":{coverage_lifecycle}" if _present(coverage_lifecycle) else ""
        parts.append(f"action_feedback_coverage_future:{coverage_signal}{suffix}")

    owner_signal = _public_value(row.get("owner_feedback_effect_signal"), default="none")
    if owner_signal == "owner_reported_template_voice_failure":
        parts.append("owner_feedback_future:style_repair_direct_only_ordinary_chat_keeps_current_anchor")
    elif _present(owner_signal):
        parts.append(f"owner_feedback_future:{owner_signal}")

    owner_response_signal = _public_value(row.get("owner_response_feedback_signal"), default="none")
    if _present(owner_response_signal):
        parts.append(f"owner_response_future:{owner_response_signal}")

    perception_route = _public_value(row.get("perception_route_hint"), default="none")
    if _present(perception_route):
        parts.append(f"perception_route_hint:{perception_route}")
    return _join_parts(parts)


def _append_source(target: list[str], label: str, value: Any) -> None:
    text = _public_value(value, default="none")
    if _present(text):
        target.append(f"{label}:{text}")


def _append_labeled_value(target: list[str], label: str, value: Any) -> None:
    text = _public_value(value, default="none")
    if _present(text):
        target.append(f"{label}:{text}")


def _status_streak(samples: list[dict[str, str]], statuses: set[str]) -> int:
    streak = 0
    for sample in reversed(samples):
        if sample.get("status") not in statuses:
            break
        streak += 1
    return streak


def _same_latest_sample(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if not left or not right:
        return False
    return (
        left.get("checked_at") == right.get("checked_at")
        and left.get("ecology_id") == right.get("ecology_id")
        and left.get("sources") == right.get("sources")
    )


def _public_sample(sample: dict[str, Any]) -> dict[str, str]:
    if not sample:
        return {
            "source": "none",
            "checked_at": "none",
            "ecology_id": "none",
            "status": "none",
            "sources": "none",
            "biases": "none",
            "future_effect": "none",
        }
    return {
        "source": _public_value(sample.get("source"), default="none"),
        "checked_at": _public_value(sample.get("checked_at"), default="none"),
        "ecology_id": _public_value(sample.get("ecology_id"), default="none"),
        "status": _public_value(sample.get("status"), default="none"),
        "sources": _public_value(sample.get("sources"), default="none"),
        "biases": _public_value(sample.get("biases"), default="none"),
        "future_effect": _public_value(sample.get("future_effect"), default="none"),
    }


def _stage7_closure(status: str, metrics: dict[str, Any], latest_status: str) -> dict[str, Any]:
    required_samples = int(metrics.get("stage7_closure_min_samples") or MIN_STAGE7_CLOSURE_SAMPLES)
    auditable_samples = int(metrics.get("feedback_required_count") or 0)
    consumed_streak = int(metrics.get("consumed_streak") or 0)
    rate = float(metrics.get("consumption_rate_pct") or 0.0)
    if status == "no_samples":
        closure_status = "no_samples"
        reason = "no_auditable_feedback_consumption_samples"
        next_step = "collect_real_feedback_consumption_samples_before_stage8"
    elif status != "pass":
        closure_status = "needs_check"
        reason = f"rolling_diagnostic_status={status}; latest={latest_status}"
        next_step = "fix_feedback_consumption_before_stage8"
    elif auditable_samples < required_samples:
        closure_status = "collecting_samples"
        reason = f"auditable_samples_below_min:{auditable_samples}/{required_samples}"
        next_step = "run_more_real_turns_until_minimum_auditable_samples"
    elif consumed_streak < required_samples:
        closure_status = "collecting_samples"
        reason = f"consumed_streak_below_min:{consumed_streak}/{required_samples}"
        next_step = "continue_observing_until_consecutive_consumed_samples"
    else:
        closure_status = "ready"
        reason = "feedback_consumption_rate_and_streak_satisfy_stage7_gate"
        next_step = "stage8_memory_governance_can_start"
    return {
        "status": closure_status,
        "ready_for_stage8": closure_status == "ready",
        "reason": reason,
        "required_samples": required_samples,
        "auditable_samples": auditable_samples,
        "consumed_streak": consumed_streak,
        "consumption_rate_pct": rate,
        "next_step": next_step,
    }


def _notes(
    status: str,
    metrics: dict[str, Any],
    latest_status: str,
    stage7_closure: dict[str, Any],
) -> list[str]:
    notes: list[str] = []
    if status == "no_samples":
        notes.append("no_auditable_feedback_consumption_samples")
    if int(metrics.get("legacy_uninstrumented_count") or 0) > 0:
        notes.append("legacy_uninstrumented_feedback_source_rows_excluded_from_rate")
    if status == "needs_check":
        notes.append(f"latest_status={latest_status}")
        notes.append(f"consumption_rate_pct={metrics.get('consumption_rate_pct', 0.0)}")
    if status == "pass":
        notes.append("recent_auditable_feedback_sources_are_consumed")
    closure_status = stage7_closure.get("status", "missing")
    if closure_status != "ready":
        notes.append(f"stage7_closure:{closure_status}:{stage7_closure.get('reason', 'missing')}")
    else:
        notes.append("stage7_closure:ready")
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


def _join_parts(parts: list[str]) -> str:
    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        text = _public_value(part, default="none")
        if not _present(text) or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return ",".join(result[:8]) if result else "none"


def _public_value(value: Any, *, default: str = "none", limit: int = 240) -> str:
    if value is None:
        return default
    text = " ".join(str(value).split()).strip()
    if not text:
        return default
    if len(text) <= limit:
        return text
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"<omitted_long_value:sha256:{digest}>"


def _present(value: Any) -> bool:
    return str(value or "").strip().lower() not in NONE_VALUES


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build XinYu feedback consumption diagnostics.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--trace-limit", type=int, default=DEFAULT_TRACE_LIMIT)
    parser.add_argument("--no-current-state", action="store_true")
    parser.add_argument("--no-latest-decision", action="store_true")
    parser.add_argument("--min-stage7-samples", type=int, default=MIN_STAGE7_CLOSURE_SAMPLES)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_feedback_consumption_diagnostics(
        args.root,
        trace_limit=max(1, int(args.trace_limit)),
        include_current_state=not args.no_current_state,
        include_latest_decision=not args.no_latest_decision,
        min_stage7_closure_samples=max(1, int(args.min_stage7_samples)),
    )
    if args.write:
        report.update(write_feedback_consumption_diagnostics(args.root, report, output=args.output))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_feedback_consumption_diagnostics(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
