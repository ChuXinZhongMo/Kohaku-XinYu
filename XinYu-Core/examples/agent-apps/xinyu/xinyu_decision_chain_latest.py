from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from xinyu_autonomy_loop_report import build_autonomy_loop_report
from xinyu_decision_chain_latest_store import append_decision_chain_latest_trace_event
from xinyu_decision_chain_latest_store import decision_chain_latest_state_path
from xinyu_decision_chain_latest_store import write_decision_chain_latest_report_text
from xinyu_decision_chain_latest_store import write_decision_chain_latest_state_text


DEFAULT_WINDOW_MINUTES = 240

NONE_VALUES = {"", "missing", "unknown", "none", "null"}
CHAIN_FIELDS = (
    "input_anchor",
    "perception_gap",
    "perception_route_hint",
    "perception_internal_consumed",
    "internal_state",
    "candidate_count",
    "selected_candidate",
    "selected_total_score",
    "runner_up_intent",
    "runner_up_gate",
    "runner_up_total_score",
    "score_margin",
    "blocked_candidate_count",
    "held_candidate_count",
    "review_gated_future_count",
    "competition_reason",
    "runner_up_not_selected_reason",
    "gate_pressure_summary",
    "blocked_intents",
    "held_intents",
    "review_gated_intents",
    "gate",
    "action_level",
    "action_result",
    "action_evidence_surface",
    "action_evidence_signal",
    "action_evidence_result",
    "action_evidence_lifecycle",
    "action_evidence_future_effect",
    "restraint_reason",
    "proactive_candidate",
    "memory_candidate",
    "action_feedback_signal",
    "action_feedback_future_effect",
    "owner_feedback_signal",
    "owner_feedback_future_effect",
    "owner_response_signal",
    "owner_response_future_effect",
    "feedback_consumption_status",
    "feedback_consumed_sources",
    "feedback_consumed_biases",
    "feedback_consumed_future_effect",
    "proactive_response_signal",
    "proactive_response_future_effect",
    "next_behavior_bias",
)
CHECK_FIELDS = (
    "perception_importance_judgment",
    "perception_gap_consumed_by_internal_state",
    "candidate_competition_auditable",
    "silence_or_hold_explained",
    "truthful_action_result",
    "feedback_changes_future_surface",
    "owner_feedback_changes_expression_strategy",
    "owner_response_changes_request_strategy",
    "feedback_consumption_auditable",
    "proactive_response_feedback_diagnostic",
)


def build_decision_chain_latest_report(
    root: Path,
    *,
    now: datetime | None = None,
    window_minutes: int = DEFAULT_WINDOW_MINUTES,
) -> dict[str, Any]:
    root = Path(root).resolve()
    now = now or datetime.now(timezone.utc)
    base_report = build_autonomy_loop_report(
        root,
        status_data=None,
        status_error="not_checked_inside_decision_chain_latest",
        now=now,
        window_minutes=max(1, int(window_minutes)),
    )
    state = base_report.get("state") if isinstance(base_report.get("state"), dict) else {}
    raw_chain = state.get("decision_chain") if isinstance(state.get("decision_chain"), dict) else {}
    chain = {field: _public_value(raw_chain.get(field, "missing")) for field in CHAIN_FIELDS}
    observed = bool(raw_chain)
    action_result = chain.get("action_result", "missing")
    action_evidence_status = _action_evidence_status(action_result)
    checks = _selected_checks(base_report)
    report = {
        "ok": observed,
        "status": "observed" if observed else "missing",
        "generated_at": now.isoformat(),
        "root": str(root),
        "window_minutes": max(1, int(window_minutes)),
        "definition": "privacy_safe_latest_decision_chain",
        "decision_chain": chain,
        "action_evidence_status": action_evidence_status,
        "source_checks": checks,
        "privacy": {
            "raw_owner_text_retained": False,
            "visible_reply_text_retained": False,
            "prompt_text_retained": False,
            "state_contains_refs_status_and_bounded_labels_only": True,
            "consciousness_claim": False,
        },
        "notes": _notes(observed, chain, action_evidence_status),
    }
    return report


def render_decision_chain_latest_report(report: dict[str, Any]) -> str:
    chain = report.get("decision_chain") if isinstance(report.get("decision_chain"), dict) else {}
    checks = report.get("source_checks") if isinstance(report.get("source_checks"), dict) else {}
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    lines = [
        "# XinYu Decision Chain Latest",
        "",
        f"- generated_at: {report.get('generated_at', 'unknown')}",
        f"- status: {report.get('status', 'unknown')}",
        f"- result: {'pass' if report.get('ok') else 'needs_check'}",
        "- claim_boundary: latest bounded decision chain only; does not claim consciousness",
        "",
        "## Decision Chain",
    ]
    for field in CHAIN_FIELDS:
        lines.append(f"- {field}: {chain.get(field, 'missing')}")
    lines.append(f"- action_evidence_status: {report.get('action_evidence_status', 'missing')}")
    lines.extend(["", "## Source Checks"])
    for field in CHECK_FIELDS:
        check = checks.get(field) if isinstance(checks.get(field), dict) else {}
        lines.append(
            f"- {field}: ok={str(check.get('ok', False)).lower()} "
            f"required={str(check.get('required', False)).lower()}"
        )
    lines.extend(["", "## Privacy Boundary"])
    for key, value in privacy.items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Notes"])
    notes = report.get("notes") if isinstance(report.get("notes"), list) else []
    lines.extend(f"- {note}" for note in notes) if notes else lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def write_decision_chain_latest(
    root: Path,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> dict[str, str]:
    root = Path(root).resolve()
    report_path = write_decision_chain_latest_report_text(
        root,
        render_decision_chain_latest_report(report),
        output=output,
    )
    _write_state(root, report, report_path=report_path)
    _append_trace(root, report)
    return {"report_path": str(report_path), "state_path": str(decision_chain_latest_state_path(root))}


def _write_state(root: Path, report: dict[str, Any], *, report_path: Path) -> None:
    chain = report.get("decision_chain") if isinstance(report.get("decision_chain"), dict) else {}
    text = f"""---
title: Decision Chain Latest State
memory_type: decision_chain_latest_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_decision_chain_latest
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, decision-chain, feedback, status]
---

# Decision Chain Latest State

## Current Decision Chain
- status: {report.get('status', 'unknown')}
- checked_at: {report.get('generated_at', 'unknown')}
- input_anchor: {chain.get('input_anchor', 'missing')}
- perception_gap: {chain.get('perception_gap', 'missing')}
- perception_route_hint: {chain.get('perception_route_hint', 'missing')}
- perception_internal_consumed: {chain.get('perception_internal_consumed', 'missing')}
- internal_state: {chain.get('internal_state', 'missing')}
- candidate_count: {chain.get('candidate_count', 'missing')}
- selected_candidate: {chain.get('selected_candidate', 'missing')}
- selected_total_score: {chain.get('selected_total_score', 'missing')}
- runner_up_intent: {chain.get('runner_up_intent', 'missing')}
- runner_up_gate: {chain.get('runner_up_gate', 'missing')}
- runner_up_total_score: {chain.get('runner_up_total_score', 'missing')}
- score_margin: {chain.get('score_margin', 'missing')}
- blocked_candidate_count: {chain.get('blocked_candidate_count', 'missing')}
- held_candidate_count: {chain.get('held_candidate_count', 'missing')}
- review_gated_future_count: {chain.get('review_gated_future_count', 'missing')}
- competition_reason: {chain.get('competition_reason', 'missing')}
- runner_up_not_selected_reason: {chain.get('runner_up_not_selected_reason', 'missing')}
- gate_pressure_summary: {chain.get('gate_pressure_summary', 'missing')}
- blocked_intents: {chain.get('blocked_intents', 'missing')}
- held_intents: {chain.get('held_intents', 'missing')}
- review_gated_intents: {chain.get('review_gated_intents', 'missing')}
- gate: {chain.get('gate', 'missing')}
- action_level: {chain.get('action_level', 'missing')}
- action_result: {chain.get('action_result', 'missing')}
- action_evidence_surface: {chain.get('action_evidence_surface', 'missing')}
- action_evidence_signal: {chain.get('action_evidence_signal', 'missing')}
- action_evidence_result: {chain.get('action_evidence_result', 'missing')}
- action_evidence_lifecycle: {chain.get('action_evidence_lifecycle', 'missing')}
- action_evidence_future_effect: {chain.get('action_evidence_future_effect', 'missing')}
- action_evidence_status: {report.get('action_evidence_status', 'missing')}
- restraint_reason: {chain.get('restraint_reason', 'missing')}
- proactive_candidate: {chain.get('proactive_candidate', 'missing')}
- memory_candidate: {chain.get('memory_candidate', 'missing')}
- action_feedback_signal: {chain.get('action_feedback_signal', 'missing')}
- action_feedback_future_effect: {chain.get('action_feedback_future_effect', 'missing')}
- owner_feedback_signal: {chain.get('owner_feedback_signal', 'missing')}
- owner_feedback_future_effect: {chain.get('owner_feedback_future_effect', 'missing')}
- owner_response_signal: {chain.get('owner_response_signal', 'missing')}
- owner_response_future_effect: {chain.get('owner_response_future_effect', 'missing')}
- feedback_consumption_status: {chain.get('feedback_consumption_status', 'missing')}
- feedback_consumed_sources: {chain.get('feedback_consumed_sources', 'missing')}
- feedback_consumed_biases: {chain.get('feedback_consumed_biases', 'missing')}
- feedback_consumed_future_effect: {chain.get('feedback_consumed_future_effect', 'missing')}
- proactive_response_signal: {chain.get('proactive_response_signal', 'missing')}
- proactive_response_future_effect: {chain.get('proactive_response_future_effect', 'missing')}
- next_behavior_bias: {chain.get('next_behavior_bias', 'missing')}

## Boundaries
- report_path: {report_path.as_posix()}
- raw_owner_text_retained: false
- visible_reply_text_retained: false
- prompt_text_retained: false
- state_contains_refs_status_and_bounded_labels_only: true
- consciousness_claim: false
"""
    write_decision_chain_latest_state_text(root, text)


def _append_trace(root: Path, report: dict[str, Any]) -> None:
    chain = report.get("decision_chain") if isinstance(report.get("decision_chain"), dict) else {}
    row = {
        "generated_at": report.get("generated_at", ""),
        "status": report.get("status", ""),
        "ok": bool(report.get("ok")),
        "input_anchor": chain.get("input_anchor", "missing"),
        "perception_gap": chain.get("perception_gap", "missing"),
        "perception_route_hint": chain.get("perception_route_hint", "missing"),
        "perception_internal_consumed": chain.get("perception_internal_consumed", "missing"),
        "selected_candidate": chain.get("selected_candidate", "missing"),
        "selected_total_score": chain.get("selected_total_score", "missing"),
        "runner_up_intent": chain.get("runner_up_intent", "missing"),
        "score_margin": chain.get("score_margin", "missing"),
        "blocked_candidate_count": chain.get("blocked_candidate_count", "missing"),
        "held_candidate_count": chain.get("held_candidate_count", "missing"),
        "review_gated_future_count": chain.get("review_gated_future_count", "missing"),
        "runner_up_not_selected_reason": chain.get("runner_up_not_selected_reason", "missing"),
        "gate_pressure_summary": chain.get("gate_pressure_summary", "missing"),
        "blocked_intents": chain.get("blocked_intents", "missing"),
        "held_intents": chain.get("held_intents", "missing"),
        "review_gated_intents": chain.get("review_gated_intents", "missing"),
        "gate": chain.get("gate", "missing"),
        "action_level": chain.get("action_level", "missing"),
        "action_result": chain.get("action_result", "missing"),
        "action_evidence_status": report.get("action_evidence_status", "missing"),
        "action_evidence_surface": chain.get("action_evidence_surface", "missing"),
        "action_evidence_signal": chain.get("action_evidence_signal", "missing"),
        "action_evidence_result": chain.get("action_evidence_result", "missing"),
        "action_evidence_lifecycle": chain.get("action_evidence_lifecycle", "missing"),
        "action_evidence_future_effect": chain.get("action_evidence_future_effect", "missing"),
        "restraint_reason": chain.get("restraint_reason", "missing"),
        "action_feedback_signal": chain.get("action_feedback_signal", "missing"),
        "owner_feedback_signal": chain.get("owner_feedback_signal", "missing"),
        "owner_response_signal": chain.get("owner_response_signal", "missing"),
        "feedback_consumption_status": chain.get("feedback_consumption_status", "missing"),
        "feedback_consumed_sources": chain.get("feedback_consumed_sources", "missing"),
        "feedback_consumed_biases": chain.get("feedback_consumed_biases", "missing"),
        "feedback_consumed_future_effect": chain.get("feedback_consumed_future_effect", "missing"),
        "proactive_response_signal": chain.get("proactive_response_signal", "missing"),
        "next_behavior_bias": chain.get("next_behavior_bias", "missing"),
        "raw_owner_text_retained": False,
        "visible_reply_text_retained": False,
        "prompt_text_retained": False,
        "consciousness_claim": False,
    }
    append_decision_chain_latest_trace_event(root, row)


def _selected_checks(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for check in report.get("checks", []):
        if not isinstance(check, dict):
            continue
        name = str(check.get("name", ""))
        if name not in CHECK_FIELDS:
            continue
        selected[name] = {
            "ok": bool(check.get("ok")),
            "required": bool(check.get("required", True)),
        }
    for name in CHECK_FIELDS:
        selected.setdefault(name, {"ok": False, "required": False})
    return selected


def _action_evidence_status(action_result: str) -> str:
    value = str(action_result or "").strip().lower()
    if value in NONE_VALUES:
        return "missing"
    if value == "unverified":
        return "unverified"
    if "needs_check" in value or any(marker in value for marker in ("failed", "timeout", "restart_required", "error")):
        return "needs_check"
    if value.startswith("local_action_result_partial"):
        return "partial"
    if value.startswith("bounded_non_action"):
        return "bounded_non_action"
    return "verified"


def _notes(observed: bool, chain: dict[str, str], action_evidence_status: str) -> list[str]:
    if not observed:
        return ["decision_chain_missing"]
    notes = [f"action_evidence:{action_evidence_status}"]
    if chain.get("gate") in {"hold_or_silence", "hold_private", "silence", "blocked"}:
        notes.append(f"restraint_reason:{chain.get('restraint_reason', 'missing')}")
    if chain.get("perception_gap") not in NONE_VALUES:
        notes.append(f"perception_gap:{chain.get('perception_gap')}")
    if chain.get("action_feedback_signal") not in NONE_VALUES:
        notes.append(f"action_feedback:{chain.get('action_feedback_signal')}")
    if chain.get("owner_feedback_signal") not in NONE_VALUES:
        notes.append(f"owner_feedback:{chain.get('owner_feedback_signal')}")
    if chain.get("feedback_consumption_status") not in NONE_VALUES:
        notes.append(f"feedback_consumption:{chain.get('feedback_consumption_status')}")
    notes.append("raw_text_not_retained")
    return notes


def _public_value(value: Any, *, limit: int = 240) -> str:
    text = " ".join(str(value if value is not None else "missing").split()).strip()
    if not text:
        return "missing"
    if len(text) <= limit:
        return text
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"<omitted_long_value:sha256:{digest}>"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build XinYu latest privacy-safe decision chain state.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--window-minutes", type=int, default=DEFAULT_WINDOW_MINUTES)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_decision_chain_latest_report(
        args.root,
        window_minutes=max(1, int(args.window_minutes)),
    )
    if args.write:
        report.update(write_decision_chain_latest(args.root, report, output=args.output))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_decision_chain_latest_report(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
