from __future__ import annotations

import argparse
import hashlib
import json
import py_compile
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from state_service import append_jsonl, atomic_write_json, atomic_write_text
from stores.self_action_queue import (
    APPROVAL_QUEUE_REL,
    BOUNDARY_ID as SELF_ACTION_QUEUE_BOUNDARY,
    append_approval_queue_event,
    read_approval_queue_rows,
)
from xinyu_self_chosen_goal_ecology import STATE_JSON_REL as GOAL_ECOLOGY_STATE_REL


GATEWAY_VERSION = 1
STATE_JSON_REL = Path("runtime/self_action_gateway/state.json")
STATE_MD_REL = Path("memory/context/self_action_gateway_state.md")
TRACE_REL = Path("runtime/self_action_gateway/trace.jsonl")
APPROVAL_HANDOFF_REL = Path("memory/context/self_action_gateway_execution_handoff.md")

LOW_LOCAL_RISK = "low_local"
APPROVAL_RISK = "approval_required"
HIGH_RISK = "high"

LOW_RISK_ACTIONS = {
    "local_py_compile_probe",
    "replay_material_probe",
    "learning_repair_probe",
    "memory_pressure_probe",
    "quiet_boundary_probe",
    "environment_trace_probe",
}
APPROVAL_ACTIONS = {
    "self_code_patch_request",
    "owner_message_draft_request",
    "stable_memory_change_request",
}
PENDING_APPROVAL = "pending_owner_approval"
APPROVED_WAITING_EXECUTION = "approved_waiting_execution"
DENIED_APPROVAL = "denied"
EXECUTED_APPROVAL = "executed"
BLOCKED_EXECUTION = "execution_blocked"


@dataclass(frozen=True, slots=True)
class ActionCandidate:
    action_id: str
    goal_id: str
    action_kind: str
    label: str
    risk: str
    requires_approval: bool
    reason: str
    tool: str
    params: dict[str, Any]
    signal_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ActionExecution:
    action_id: str
    action_kind: str
    goal_id: str
    status: str
    result: str
    duration_ms: int
    summary: tuple[str, ...]
    report_ref: str
    error_code: str = ""


def run_self_action_gateway(
    root: Path,
    *,
    checked_at: str | None = None,
    trigger: str = "manual",
    execute_low_risk: bool = True,
    write_state: bool = True,
) -> dict[str, Any]:
    root = Path(root)
    checked_at = _timestamp_or_now_iso(checked_at)
    goal_state = _read_json(root / GOAL_ECOLOGY_STATE_REL, default={})
    selected_goal_id = _safe_token(goal_state.get("last_selected_goal_id")) if isinstance(goal_state, dict) else ""
    candidates = build_action_candidates(root, selected_goal_id=selected_goal_id, checked_at=checked_at)
    low_risk = [candidate for candidate in candidates if candidate.risk == LOW_LOCAL_RISK and not candidate.requires_approval]
    approval_required = [candidate for candidate in candidates if candidate.requires_approval]

    executions: list[ActionExecution] = []
    queued: list[dict[str, Any]] = []
    skipped_approvals: list[str] = []
    state = _load_state(root)
    if execute_low_risk:
        for candidate in low_risk[:1]:
            executions.append(_execute_low_risk_action(root, candidate, checked_at=checked_at))
    for candidate in approval_required:
        queued_item = _queue_approval_if_new(root, state, candidate, checked_at=checked_at)
        if queued_item.get("queued"):
            queued.append(queued_item)
        else:
            skipped_approvals.append(_safe_str(queued_item.get("reason"), "duplicate"))

    result = {
        "accepted": True,
        "status": "completed",
        "checked_at": checked_at,
        "trigger": trigger,
        "selected_goal_id": selected_goal_id or "none",
        "candidate_count": len(candidates),
        "executed_action_count": len(executions),
        "queued_approval_count": len(queued),
        "skipped_approval_count": len(skipped_approvals),
        "low_risk_results": [asdict(item) for item in executions],
        "approval_queue_items": queued,
        "notes": _result_notes(selected_goal_id, executions, queued, skipped_approvals),
    }
    if write_state:
        state = _update_state(
            state,
            checked_at=checked_at,
            selected_goal_id=selected_goal_id,
            candidates=candidates,
            executions=executions,
            queued=queued,
            skipped_approvals=skipped_approvals,
        )
        state = _with_approval_overview(root, state, checked_at=checked_at)
        _persist_state(root, state)
        _write_state_markdown(root, state)
        append_jsonl(root / TRACE_REL, {"event_kind": "self_action_gateway_run", "version": GATEWAY_VERSION, **result})
    return result


def list_self_action_approvals(root: Path) -> dict[str, Any]:
    root = Path(root)
    snapshot = _approval_queue_snapshot(root)
    overview = _approval_overview_from_snapshot(snapshot)
    return {
        "accepted": True,
        "status": "completed",
        "approval_queue": overview,
        "items": [_public_queue_item(item) for item in _sorted_queue_items(snapshot)],
    }


def decide_self_action_approval(
    root: Path,
    *,
    queue_id: str = "latest",
    decision: str,
    decided_at: str | None = None,
    decided_by: str = "owner",
    reason: str = "",
    execute: bool = False,
    write_state: bool = True,
) -> dict[str, Any]:
    root = Path(root)
    decided_at = _timestamp_or_now_iso(decided_at)
    normalized_decision = _safe_token(decision)
    if normalized_decision not in {"approved", "denied"}:
        return {
            "accepted": False,
            "status": "blocked",
            "reason": "unknown_decision",
            "notes": ["self_action_approval:blocked/unknown_decision"],
        }
    snapshot = _approval_queue_snapshot(root)
    item = _resolve_queue_item(snapshot, queue_id, allowed_statuses={PENDING_APPROVAL})
    if not item:
        return {
            "accepted": False,
            "status": "blocked",
            "reason": "no_pending_approval",
            "queue_id": queue_id,
            "notes": ["self_action_approval:blocked/no_pending_approval"],
        }
    approval_id = "selfaction-decision-" + _hash_json(
        {
            "queue_id": item.get("queue_id"),
            "decision": normalized_decision,
            "decided_at": decided_at,
            "decided_by": decided_by,
        },
        length=16,
    )
    event = {
        "event_kind": "self_action_approval_decided",
        "version": GATEWAY_VERSION,
        "queue_id": item.get("queue_id"),
        "approval_id": approval_id,
        "decided_at": decided_at,
        "decided_by": _compact(decided_by, 80),
        "decision": normalized_decision,
        "status": APPROVED_WAITING_EXECUTION if normalized_decision == "approved" else DENIED_APPROVAL,
        "reason": _compact(reason, 260),
        "goal_id": item.get("goal_id"),
        "action_kind": item.get("action_kind"),
        "approval_scope": _safe_str(item.get("approval_scope")),
    }
    append_approval_queue_event(root, event)
    trace_event = dict(event)
    trace_event["queue_event_kind"] = trace_event.pop("event_kind")
    append_jsonl(root / TRACE_REL, {"event_kind": "self_action_approval_decision", **trace_event})
    result: dict[str, Any] = {
        "accepted": True,
        "status": "completed",
        "queue_id": item.get("queue_id"),
        "approval_id": approval_id,
        "decision": normalized_decision,
        "execute_requested": bool(execute),
        "notes": [f"self_action_approval:{normalized_decision}/{item.get('queue_id')}"],
    }
    if write_state:
        _refresh_state_after_approval_change(root, checked_at=decided_at)
    if execute and normalized_decision == "approved":
        result["execution"] = execute_approved_self_actions(
            root,
            queue_id=_safe_str(item.get("queue_id")),
            checked_at=decided_at,
            write_state=write_state,
        )
    return result


def execute_approved_self_actions(
    root: Path,
    *,
    queue_id: str = "next",
    checked_at: str | None = None,
    write_state: bool = True,
) -> dict[str, Any]:
    root = Path(root)
    checked_at = _timestamp_or_now_iso(checked_at)
    snapshot = _approval_queue_snapshot(root)
    if _safe_token(queue_id) == "all":
        targets = [
            item
            for item in _sorted_queue_items(snapshot)
            if _safe_str(item.get("status")) == APPROVED_WAITING_EXECUTION
        ]
    else:
        item = _resolve_queue_item(snapshot, queue_id, allowed_statuses={APPROVED_WAITING_EXECUTION})
        targets = [item] if item else []
    if not targets:
        return {
            "accepted": False,
            "status": "blocked",
            "reason": "no_approved_action",
            "queue_id": queue_id,
            "executed_count": 0,
            "notes": ["self_action_approval_execution:blocked/no_approved_action"],
        }

    executions: list[dict[str, Any]] = []
    for item in targets:
        execution = _execute_approved_queue_item(root, item, checked_at=checked_at)
        append_approval_queue_event(
            root,
            {
                "event_kind": "self_action_approval_executed",
                "version": GATEWAY_VERSION,
                **execution,
            },
        )
        append_jsonl(
            root / TRACE_REL,
            {
                "event_kind": "self_action_approval_execution",
                "version": GATEWAY_VERSION,
                "checked_at": checked_at,
                **execution,
            },
        )
        executions.append(execution)
    if write_state:
        _refresh_state_after_approval_change(root, checked_at=checked_at)
    return {
        "accepted": True,
        "status": "completed",
        "checked_at": checked_at,
        "executed_count": len(executions),
        "executions": executions,
        "notes": [f"self_action_approval_execution:completed/{len(executions)}"],
    }


def build_action_candidates(root: Path, *, selected_goal_id: str, checked_at: str | None = None) -> list[ActionCandidate]:
    del checked_at
    goal = _safe_token(selected_goal_id)
    if not goal:
        return []
    low = _low_risk_candidate_for_goal(root, goal)
    high = _approval_candidate_for_goal(root, goal)
    return [candidate for candidate in (low, high) if candidate is not None]


def _low_risk_candidate_for_goal(root: Path, goal_id: str) -> ActionCandidate | None:
    if goal_id == "continue_bounded_work":
        targets = [
            rel
            for rel in (
                "xinyu_self_chosen_goal_ecology.py",
                "xinyu_goal_outcome_observer.py",
                "xinyu_self_action_gateway.py",
            )
            if (root / rel).exists()
        ]
        return _candidate(
            goal_id,
            "local_py_compile_probe",
            "run bounded py_compile probe",
            LOW_LOCAL_RISK,
            False,
            "A technical goal can verify the local Python surface without editing code.",
            "py_compile",
            {"targets": targets, "max_targets": 3},
            ("xinyu_self_action_gateway.py:py_compile",),
        )
    if goal_id == "curate_failure_replay":
        return _candidate(
            goal_id,
            "replay_material_probe",
            "inspect replay material counts",
            LOW_LOCAL_RISK,
            False,
            "Replay work can inspect local summary counts before proposing fixture changes.",
            "state_probe",
            {"paths": ["runtime/replay_candidates/chat_replay_export_summary.json"]},
            ("runtime/replay_candidates/chat_replay_export_summary.json:counts",),
        )
    if goal_id == "absorb_feedback_repair":
        return _candidate(
            goal_id,
            "learning_repair_probe",
            "inspect learning repair state",
            LOW_LOCAL_RISK,
            False,
            "Feedback repair can inspect the closed-loop state before any memory rewrite.",
            "state_probe",
            {"paths": ["memory/self/learning_closed_loop_state.md"]},
            ("memory/self/learning_closed_loop_state.md:fields",),
        )
    if goal_id == "review_memory_pressure":
        return _candidate(
            goal_id,
            "memory_pressure_probe",
            "inspect memory pressure traces",
            LOW_LOCAL_RISK,
            False,
            "Memory pressure review can count local traces without promoting memory.",
            "trace_probe",
            {"paths": ["runtime/memory_self_review_trace.jsonl", "runtime/contextual_recall_trace.jsonl"]},
            ("runtime/memory_self_review_trace.jsonl:count", "runtime/contextual_recall_trace.jsonl:count"),
        )
    if goal_id == "quiet_presence":
        return _candidate(
            goal_id,
            "quiet_boundary_probe",
            "inspect quiet boundary",
            LOW_LOCAL_RISK,
            False,
            "Quiet presence can verify the local posture boundary without outward contact.",
            "state_probe",
            {"paths": ["memory/context/current_life_posture.md"]},
            ("memory/context/current_life_posture.md:fields",),
        )
    if goal_id == "observe_environment":
        return _candidate(
            goal_id,
            "environment_trace_probe",
            "inspect environment traces",
            LOW_LOCAL_RISK,
            False,
            "Observation can count local traces without sending messages.",
            "trace_probe",
            {"paths": ["runtime/self_presence_trace.jsonl", "runtime/qq_inbound_trace.jsonl"]},
            ("runtime/self_presence_trace.jsonl:count", "runtime/qq_inbound_trace.jsonl:count"),
        )
    return None


def _approval_candidate_for_goal(root: Path, goal_id: str) -> ActionCandidate | None:
    del root
    if goal_id == "continue_bounded_work":
        return _candidate(
            goal_id,
            "self_code_patch_request",
            "request approval for focused self-code patch",
            APPROVAL_RISK,
            True,
            "Code modification crosses the write-code boundary and needs owner approval.",
            "approval_queue",
            {"approval_scope": "focused_xinyu_app_patch", "executor": "codex_after_owner_approval"},
            ("memory/context/self_code_approval_state.md:approval_rule",),
        )
    if goal_id == "curate_failure_replay":
        return _candidate(
            goal_id,
            "self_code_patch_request",
            "request approval for replay fixture promotion patch",
            APPROVAL_RISK,
            True,
            "Fixture promotion changes test/code artifacts and needs approval.",
            "approval_queue",
            {"approval_scope": "replay_fixture_or_test_patch", "executor": "codex_after_owner_approval"},
            ("runtime/replay_candidates/chat_replay_export_summary.json:counts",),
        )
    if goal_id == "absorb_feedback_repair":
        return _candidate(
            goal_id,
            "stable_memory_change_request",
            "request approval for stable repair memory change",
            APPROVAL_RISK,
            True,
            "Stable memory or personality changes require explicit approval.",
            "approval_queue",
            {"approval_scope": "stable_memory_or_voice_repair", "executor": "owner_review"},
            ("memory/self/learning_closed_loop_state.md:fields",),
        )
    if goal_id == "observe_environment":
        return _candidate(
            goal_id,
            "owner_message_draft_request",
            "request approval for outward owner message",
            APPROVAL_RISK,
            True,
            "Outward messaging crosses the send boundary and must stay queued.",
            "approval_queue",
            {"approval_scope": "owner_private_message_draft", "executor": "owner_approval_required"},
            ("memory/context/proactive_request_state.md:status",),
        )
    return None


def _candidate(
    goal_id: str,
    action_kind: str,
    label: str,
    risk: str,
    requires_approval: bool,
    reason: str,
    tool: str,
    params: dict[str, Any],
    signal_refs: tuple[str, ...],
) -> ActionCandidate:
    action_id = "selfact-" + _hash_json(
        {
            "goal_id": goal_id,
            "action_kind": action_kind,
            "label": label,
            "risk": risk,
            "requires_approval": requires_approval,
            "params": params,
        },
        length=16,
    )
    return ActionCandidate(
        action_id=action_id,
        goal_id=goal_id,
        action_kind=action_kind,
        label=label,
        risk=risk,
        requires_approval=requires_approval,
        reason=reason,
        tool=tool,
        params=dict(params),
        signal_refs=signal_refs,
    )


def _execute_low_risk_action(root: Path, candidate: ActionCandidate, *, checked_at: str) -> ActionExecution:
    started = time.perf_counter()
    try:
        if candidate.action_kind == "local_py_compile_probe":
            result, summary, error = _execute_py_compile_probe(root, candidate)
        elif candidate.action_kind in {"replay_material_probe", "learning_repair_probe", "quiet_boundary_probe"}:
            result, summary, error = _execute_state_probe(root, candidate)
        elif candidate.action_kind in {"memory_pressure_probe", "environment_trace_probe"}:
            result, summary, error = _execute_trace_probe(root, candidate)
        else:
            result, summary, error = "blocked", ("low-risk action is not whitelisted",), "action_not_whitelisted"
    except Exception as exc:
        result, summary, error = "failed", (f"executor exception: {type(exc).__name__}",), type(exc).__name__
    duration_ms = int((time.perf_counter() - started) * 1000)
    status = "executed" if result in {"success", "failed"} else "blocked"
    execution = ActionExecution(
        action_id=candidate.action_id,
        action_kind=candidate.action_kind,
        goal_id=candidate.goal_id,
        status=status,
        result=result,
        duration_ms=duration_ms,
        summary=tuple(summary),
        report_ref=f"runtime/self_action_gateway/trace.jsonl:{checked_at}",
        error_code=error,
    )
    append_jsonl(
        root / TRACE_REL,
        {
            "event_kind": "self_action_executed",
            "version": GATEWAY_VERSION,
            "checked_at": checked_at,
            **asdict(execution),
        },
    )
    return execution


def _execute_py_compile_probe(root: Path, candidate: ActionCandidate) -> tuple[str, tuple[str, ...], str]:
    targets = [_safe_str(item) for item in candidate.params.get("targets", []) if _safe_str(item)]
    targets = targets[: max(0, _safe_int(candidate.params.get("max_targets"), 3))]
    if not targets:
        return "blocked", ("no existing py_compile targets",), "no_targets"
    compiled: list[str] = []
    for rel in targets:
        path = root / rel
        if not _is_safe_relative(rel) or not path.exists():
            return "blocked", (f"target not allowed or missing: {_safe_token(rel)}",), "target_not_allowed"
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError:
            return "failed", (f"py_compile failed for {rel}",), "py_compile_failed"
        compiled.append(rel)
    return "success", (f"py_compile ok for {len(compiled)} target(s)",), ""


def _execute_state_probe(root: Path, candidate: ActionCandidate) -> tuple[str, tuple[str, ...], str]:
    paths = [_safe_str(item) for item in candidate.params.get("paths", []) if _safe_str(item)]
    if not paths:
        return "blocked", ("no state paths configured",), "no_paths"
    summaries: list[str] = []
    for rel in paths[:4]:
        if not _is_safe_relative(rel):
            return "blocked", (f"path not allowed: {_safe_token(rel)}",), "path_not_allowed"
        text = _read_text(root / rel, limit=6000)
        fields = _markdown_fields(text)
        summaries.append(f"{rel}: exists={str(bool(text)).lower()} fields={len(fields)} hash={_hash_text(text, 10) if text else 'none'}")
    return "success", tuple(summaries), ""


def _execute_trace_probe(root: Path, candidate: ActionCandidate) -> tuple[str, tuple[str, ...], str]:
    paths = [_safe_str(item) for item in candidate.params.get("paths", []) if _safe_str(item)]
    if not paths:
        return "blocked", ("no trace paths configured",), "no_paths"
    summaries: list[str] = []
    for rel in paths[:4]:
        if not _is_safe_relative(rel):
            return "blocked", (f"path not allowed: {_safe_token(rel)}",), "path_not_allowed"
        rows, last_event = _jsonl_summary(root / rel)
        summaries.append(f"{rel}: rows={rows} last={last_event or 'none'}")
    return "success", tuple(summaries), ""


def _queue_approval_if_new(root: Path, state: dict[str, Any], candidate: ActionCandidate, *, checked_at: str) -> dict[str, Any]:
    signature = _approval_signature(candidate)
    queued_signatures = state.get("queued_signatures") if isinstance(state.get("queued_signatures"), list) else []
    if signature in queued_signatures:
        return {"queued": False, "reason": "duplicate_approval_candidate", "signature": signature}
    item = {
        "queue_id": "selfaction-approval-" + signature[:16],
        "queued_at": checked_at,
        "status": "pending_owner_approval",
        "signature": signature,
        "goal_id": candidate.goal_id,
        "action_kind": candidate.action_kind,
        "label": candidate.label,
        "risk": HIGH_RISK,
        "requires_approval": True,
        "reason": candidate.reason,
        "approval_rule": "owner approval required before outward message, code edit, tool delegation, or stable memory rewrite",
        "tool": candidate.tool,
        "params": _scrub_params(candidate.params),
        "signal_refs": list(candidate.signal_refs),
    }
    append_approval_queue_event(root, {"event_kind": "self_action_approval_queued", "version": GATEWAY_VERSION, **item})
    queued_signatures.append(signature)
    state["queued_signatures"] = queued_signatures[-50:]
    return {"queued": True, **item}


def _approval_signature(candidate: ActionCandidate) -> str:
    return _hash_json(
        {
            "goal_id": candidate.goal_id,
            "action_kind": candidate.action_kind,
            "approval_scope": candidate.params.get("approval_scope"),
        },
        length=24,
    )


def _approval_queue_snapshot(root: Path) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for index, row in read_approval_queue_rows(root):
        queue_id = _safe_str(row.get("queue_id")).strip()
        if not queue_id:
            continue
        event_kind = _safe_str(row.get("event_kind"))
        if event_kind == "self_action_approval_queued":
            current = items.get(queue_id, {})
            queued = {
                "_index": index,
                "queue_id": queue_id,
                "queued_at": _safe_str(row.get("queued_at")),
                "status": PENDING_APPROVAL,
                "signature": _safe_str(row.get("signature")),
                "goal_id": _safe_str(row.get("goal_id")),
                "action_kind": _safe_str(row.get("action_kind")),
                "label": _safe_str(row.get("label")),
                "risk": _safe_str(row.get("risk"), HIGH_RISK),
                "reason": _safe_str(row.get("reason")),
                "approval_rule": _safe_str(row.get("approval_rule")),
                "tool": _safe_str(row.get("tool")),
                "params": row.get("params") if isinstance(row.get("params"), dict) else {},
                "signal_refs": row.get("signal_refs") if isinstance(row.get("signal_refs"), list) else [],
            }
            queued.update({key: value for key, value in current.items() if key.startswith("decision_") or key.startswith("execution_")})
            if _safe_str(current.get("status")) in {APPROVED_WAITING_EXECUTION, DENIED_APPROVAL, EXECUTED_APPROVAL, BLOCKED_EXECUTION}:
                queued["status"] = current["status"]
            items[queue_id] = queued
            continue
        item = items.setdefault(queue_id, {"_index": index, "queue_id": queue_id, "status": "unknown"})
        if event_kind == "self_action_approval_decided":
            decision = _safe_token(row.get("decision"))
            item["decision"] = decision
            item["decision_at"] = _safe_str(row.get("decided_at"))
            item["decision_by"] = _safe_str(row.get("decided_by"))
            item["approval_id"] = _safe_str(row.get("approval_id"))
            item["decision_reason"] = _safe_str(row.get("reason"))
            item["goal_id"] = item.get("goal_id") or _safe_str(row.get("goal_id"))
            item["action_kind"] = item.get("action_kind") or _safe_str(row.get("action_kind"))
            item["approval_scope"] = _safe_str(row.get("approval_scope"))
            item["status"] = APPROVED_WAITING_EXECUTION if decision == "approved" else DENIED_APPROVAL
            continue
        if event_kind == "self_action_approval_executed":
            execution_status = _safe_str(row.get("status"))
            item["execution_at"] = _safe_str(row.get("checked_at"))
            item["execution_result"] = _safe_str(row.get("result"))
            item["execution_report_ref"] = _safe_str(row.get("report_ref"))
            item["execution_error_code"] = _safe_str(row.get("error_code"))
            item["execution_summary"] = row.get("summary") if isinstance(row.get("summary"), list) else []
            item["status"] = EXECUTED_APPROVAL if execution_status == EXECUTED_APPROVAL else BLOCKED_EXECUTION
            continue
    return items


def _sorted_queue_items(snapshot: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(snapshot.values(), key=lambda item: _safe_int(item.get("_index"), 0))


def _public_queue_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "queue_id": _safe_str(item.get("queue_id")),
        "queued_at": _safe_str(item.get("queued_at")),
        "status": _safe_str(item.get("status"), "unknown"),
        "goal_id": _safe_str(item.get("goal_id")),
        "action_kind": _safe_str(item.get("action_kind")),
        "label": _compact(item.get("label"), 160),
        "risk": _safe_str(item.get("risk"), HIGH_RISK),
        "reason": _compact(item.get("reason"), 220),
        "approval_scope": _safe_str(item.get("approval_scope") or _params(item).get("approval_scope")),
        "approval_id": _safe_str(item.get("approval_id")),
        "execution_result": _safe_str(item.get("execution_result")),
        "execution_report_ref": _safe_str(item.get("execution_report_ref")),
    }


def _params(item: dict[str, Any]) -> dict[str, Any]:
    params = item.get("params")
    return params if isinstance(params, dict) else {}


def _approval_overview_from_snapshot(snapshot: dict[str, dict[str, Any]]) -> dict[str, Any]:
    items = _sorted_queue_items(snapshot)
    counts = {
        "pending_count": 0,
        "approved_waiting_execution_count": 0,
        "executed_count": 0,
        "denied_count": 0,
        "blocked_execution_count": 0,
        "total_count": len(items),
    }
    latest_pending = ""
    latest_approved = ""
    latest_executed = ""
    for item in items:
        status = _safe_str(item.get("status"))
        queue_id = _safe_str(item.get("queue_id"))
        if status == PENDING_APPROVAL:
            counts["pending_count"] += 1
            latest_pending = queue_id
        elif status == APPROVED_WAITING_EXECUTION:
            counts["approved_waiting_execution_count"] += 1
            latest_approved = queue_id
        elif status == EXECUTED_APPROVAL:
            counts["executed_count"] += 1
            latest_executed = queue_id
        elif status == DENIED_APPROVAL:
            counts["denied_count"] += 1
        elif status == BLOCKED_EXECUTION:
            counts["blocked_execution_count"] += 1
    return {
        **counts,
        "latest_pending_queue_id": latest_pending or "none",
        "latest_approved_queue_id": latest_approved or "none",
        "latest_executed_queue_id": latest_executed or "none",
    }


def _resolve_queue_item(
    snapshot: dict[str, dict[str, Any]],
    queue_id: str,
    *,
    allowed_statuses: set[str],
) -> dict[str, Any] | None:
    selector = _safe_str(queue_id, "latest").strip()
    items = [item for item in _sorted_queue_items(snapshot) if _safe_str(item.get("status")) in allowed_statuses]
    if selector in {"", "latest"}:
        return items[-1] if items else None
    if selector == "next":
        return items[0] if items else None
    item = snapshot.get(selector)
    if item and _safe_str(item.get("status")) in allowed_statuses:
        return item
    return None


def _with_approval_overview(root: Path, state: dict[str, Any], *, checked_at: str) -> dict[str, Any]:
    snapshot = _approval_queue_snapshot(root)
    overview = _approval_overview_from_snapshot(snapshot)
    updated = dict(state)
    updated["updated_at"] = _timestamp_or_now_iso(checked_at)
    updated["pending_approval_count"] = overview["pending_count"]
    updated["approved_approval_count"] = overview["approved_waiting_execution_count"]
    updated["executed_approval_count"] = overview["executed_count"]
    updated["denied_approval_count"] = overview["denied_count"]
    updated["blocked_execution_count"] = overview["blocked_execution_count"]
    updated["approval_queue"] = overview
    latest_executed = _latest_item_by_id(snapshot, _safe_str(overview.get("latest_executed_queue_id")))
    if latest_executed:
        updated["latest_approval_execution"] = _public_queue_item(latest_executed)
    return updated


def _latest_item_by_id(snapshot: dict[str, dict[str, Any]], queue_id: str) -> dict[str, Any] | None:
    if not queue_id or queue_id == "none":
        return None
    return snapshot.get(queue_id)


def _refresh_state_after_approval_change(root: Path, *, checked_at: str) -> None:
    state = _with_approval_overview(root, _load_state(root), checked_at=checked_at)
    _persist_state(root, state)
    _write_state_markdown(root, state)


def _execute_approved_queue_item(root: Path, item: dict[str, Any], *, checked_at: str) -> dict[str, Any]:
    started = time.perf_counter()
    action_kind = _safe_str(item.get("action_kind"))
    queue_id = _safe_str(item.get("queue_id"))
    status = EXECUTED_APPROVAL
    result = "handoff_created"
    error_code = ""
    report_ref = str(APPROVAL_HANDOFF_REL).replace("\\", "/")
    if action_kind == "self_code_patch_request":
        summary = [
            "approved code action converted to local Codex handoff",
            "no source file was edited by the gateway",
        ]
        _write_execution_handoff(
            root,
            item,
            checked_at=checked_at,
            execution_mode="codex_handoff_ticket",
            permitted_effect="Codex may inspect and patch the focused XinYu app surface after owner approval.",
            blocked_effect="The gateway itself must not edit source files.",
            next_executor="codex_after_owner_approval",
            summary=summary,
        )
    elif action_kind == "stable_memory_change_request":
        summary = [
            "approved memory action converted to review packet",
            "stable memory remains unchanged until a concrete patch is applied",
        ]
        _write_execution_handoff(
            root,
            item,
            checked_at=checked_at,
            execution_mode="stable_memory_review_ticket",
            permitted_effect="Prepare a reviewed memory or voice repair proposal.",
            blocked_effect="Do not rewrite stable memory directly from the gateway.",
            next_executor="owner_review_then_codex_or_memory_writer",
            summary=summary,
        )
    elif action_kind == "owner_message_draft_request":
        summary = [
            "approved outward action converted to draft ticket",
            "no outbound message was sent by the gateway",
        ]
        _write_execution_handoff(
            root,
            item,
            checked_at=checked_at,
            execution_mode="owner_message_draft_ticket",
            permitted_effect="Draft owner-private message content for later explicit sending.",
            blocked_effect="Do not enqueue or send outward messages from the gateway.",
            next_executor="owner_visible_message_review",
            summary=summary,
        )
    else:
        status = BLOCKED_EXECUTION
        result = "blocked"
        error_code = "unsupported_approved_action"
        summary = [f"approved action kind is unsupported: {_safe_token(action_kind)}"]
        report_ref = ""
    duration_ms = int((time.perf_counter() - started) * 1000)
    return {
        "queue_id": queue_id,
        "approval_id": _safe_str(item.get("approval_id")),
        "checked_at": checked_at,
        "goal_id": _safe_str(item.get("goal_id")),
        "action_kind": action_kind,
        "status": status,
        "result": result,
        "duration_ms": duration_ms,
        "summary": summary,
        "report_ref": report_ref,
        "error_code": error_code,
    }


def _write_execution_handoff(
    root: Path,
    item: dict[str, Any],
    *,
    checked_at: str,
    execution_mode: str,
    permitted_effect: str,
    blocked_effect: str,
    next_executor: str,
    summary: list[str],
) -> None:
    params = _params(item)
    lines = [
        "---",
        "title: Self Action Gateway Execution Handoff",
        "memory_type: self_action_gateway_execution_handoff",
        "time_scope: short_term",
        "subject_ids: [xinyu]",
        "protected: true",
        "source: xinyu_self_action_gateway",
        f"updated_at: {_timestamp_or_now_iso(checked_at)}",
        "status: active",
        "tags: [initiative, action, local-control, approval]",
        "---",
        "",
        "# Self Action Gateway Execution Handoff",
        "",
        "## Approved Action",
        f"- queue_id: {_safe_str(item.get('queue_id'))}",
        f"- approval_id: {_safe_str(item.get('approval_id'))}",
        f"- goal_id: {_safe_str(item.get('goal_id'))}",
        f"- action_kind: {_safe_str(item.get('action_kind'))}",
        f"- approval_scope: {_safe_str(item.get('approval_scope') or params.get('approval_scope'), 'none')}",
        f"- execution_mode: {_safe_str(execution_mode)}",
        f"- next_executor: {_safe_str(next_executor)}",
        "",
        "## Local Control Boundary",
        f"- permitted_effect: {_compact(permitted_effect, 240)}",
        f"- blocked_effect: {_compact(blocked_effect, 240)}",
        "- gateway_effect: local ticket and trace only",
        "",
        "## Summary",
    ]
    lines.extend(f"- {_compact(item, 220)}" for item in summary)
    signal_refs = item.get("signal_refs") if isinstance(item.get("signal_refs"), list) else []
    if signal_refs:
        lines.extend(["", "## Signal Refs"])
        lines.extend(f"- {_compact(ref, 180)}" for ref in signal_refs[:8])
    atomic_write_text(root / APPROVAL_HANDOFF_REL, "\n".join(lines))


def _update_state(
    state: dict[str, Any],
    *,
    checked_at: str,
    selected_goal_id: str,
    candidates: list[ActionCandidate],
    executions: list[ActionExecution],
    queued: list[dict[str, Any]],
    skipped_approvals: list[str],
) -> dict[str, Any]:
    history = state.get("history") if isinstance(state.get("history"), list) else []
    run_record = {
        "checked_at": checked_at,
        "selected_goal_id": selected_goal_id or "none",
        "candidate_count": len(candidates),
        "executed_action_count": len(executions),
        "queued_approval_count": len(queued),
        "skipped_approval_count": len(skipped_approvals),
        "execution_results": [asdict(item) for item in executions],
        "queued_approval_ids": [_safe_str(item.get("queue_id")) for item in queued],
    }
    updated = dict(state)
    updated["version"] = GATEWAY_VERSION
    updated["updated_at"] = _timestamp_or_now_iso(checked_at)
    updated["last_run"] = run_record
    updated["last_candidates"] = [asdict(item) for item in candidates]
    updated["history"] = [*history, run_record][-50:]
    updated["pending_approval_count"] = _pending_approval_count(updated)
    updated["policy"] = {
        "low_risk_auto_execute": "read_state_trace_and_bounded_py_compile_only",
        "high_risk_boundary": "queue_only_until_owner_approval",
        "blocked_without_approval": "outward_message_code_edit_tool_delegation_stable_memory_rewrite",
    }
    return updated


def _pending_approval_count(state: dict[str, Any]) -> int:
    signatures = state.get("queued_signatures") if isinstance(state.get("queued_signatures"), list) else []
    return len(signatures)


def _result_notes(
    selected_goal_id: str,
    executions: list[ActionExecution],
    queued: list[dict[str, Any]],
    skipped_approvals: list[str],
) -> list[str]:
    notes = [f"self_action:goal/{selected_goal_id or 'none'}"]
    if executions:
        first = executions[0]
        result = "failed" if first.result == "failed" else first.result
        notes.append(f"self_action:executed/{first.goal_id}/{result}")
    else:
        notes.append("self_action:executed/none/skipped")
    if queued:
        notes.append(f"self_action:approval_queued/{queued[0].get('goal_id', 'none')}/{queued[0].get('action_kind', 'unknown')}")
    if skipped_approvals:
        notes.append(f"self_action:approval_skipped/{skipped_approvals[0]}")
    return notes


def _write_state_markdown(root: Path, state: dict[str, Any]) -> None:
    last = state.get("last_run") if isinstance(state.get("last_run"), dict) else {}
    candidates = state.get("last_candidates") if isinstance(state.get("last_candidates"), list) else []
    approval_queue = state.get("approval_queue") if isinstance(state.get("approval_queue"), dict) else {}
    latest_execution = state.get("latest_approval_execution") if isinstance(state.get("latest_approval_execution"), dict) else {}
    lines = [
        "---",
        "title: Self Action Gateway State",
        "memory_type: self_action_gateway_state",
        "time_scope: short_term",
        "subject_ids: [xinyu]",
        "protected: true",
        "source: xinyu_self_action_gateway",
        f"updated_at: {_safe_str(state.get('updated_at'))}",
        "status: active",
        "tags: [initiative, action, local-control, approval]",
        "---",
        "",
        "# Self Action Gateway State",
        "",
        "## Last Run",
        f"- checked_at: {_safe_str(last.get('checked_at'), 'none')}",
        f"- selected_goal_id: {_safe_str(last.get('selected_goal_id'), 'none')}",
        f"- candidate_count: {_safe_str(last.get('candidate_count'), '0')}",
        f"- executed_action_count: {_safe_str(last.get('executed_action_count'), '0')}",
        f"- queued_approval_count: {_safe_str(last.get('queued_approval_count'), '0')}",
        f"- pending_approval_count: {_safe_str(state.get('pending_approval_count'), '0')}",
        f"- approved_waiting_execution_count: {_safe_str(state.get('approved_approval_count'), '0')}",
        f"- executed_approval_count: {_safe_str(state.get('executed_approval_count'), '0')}",
        "",
        "## Candidate Actions",
    ]
    for candidate in candidates:
        lines.append(
            "- "
            f"{_safe_str(candidate.get('action_kind'))}: "
            f"goal={_safe_str(candidate.get('goal_id'))} "
            f"risk={_safe_str(candidate.get('risk'))} "
            f"requires_approval={str(bool(candidate.get('requires_approval'))).lower()}"
        )
    lines.extend(
        [
            "",
            "## Approval Queue",
            f"- pending_count: {_safe_str(approval_queue.get('pending_count'), '0')}",
            f"- approved_waiting_execution_count: {_safe_str(approval_queue.get('approved_waiting_execution_count'), '0')}",
            f"- executed_count: {_safe_str(approval_queue.get('executed_count'), '0')}",
            f"- denied_count: {_safe_str(approval_queue.get('denied_count'), '0')}",
            f"- blocked_execution_count: {_safe_str(approval_queue.get('blocked_execution_count'), '0')}",
            f"- latest_pending_queue_id: {_safe_str(approval_queue.get('latest_pending_queue_id'), 'none')}",
            f"- latest_approved_queue_id: {_safe_str(approval_queue.get('latest_approved_queue_id'), 'none')}",
            f"- latest_executed_queue_id: {_safe_str(approval_queue.get('latest_executed_queue_id'), 'none')}",
        ]
    )
    if latest_execution:
        lines.extend(
            [
                "",
                "## Latest Approved Execution",
                f"- queue_id: {_safe_str(latest_execution.get('queue_id'), 'none')}",
                f"- action_kind: {_safe_str(latest_execution.get('action_kind'), 'none')}",
                f"- execution_result: {_safe_str(latest_execution.get('execution_result'), 'none')}",
                f"- execution_report_ref: {_safe_str(latest_execution.get('execution_report_ref'), 'none')}",
            ]
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "- low_risk_auto_execute: read state, read traces, bounded py_compile only",
            "- queued_only_until_approval: outward messages, code edits, delegated tool work, and stable memory rewrites",
            "- approved_execution: local ticket and trace first; no direct send or source edit by gateway",
            "- approval_queue: memory/context/self_action_gateway_approval_queue.jsonl",
            "- approval_handoff: memory/context/self_action_gateway_execution_handoff.md",
        ]
    )
    atomic_write_text(root / STATE_MD_REL, "\n".join(lines))


def _load_state(root: Path) -> dict[str, Any]:
    data = _read_json(root / STATE_JSON_REL, default={})
    if not isinstance(data, dict):
        data = {}
    data["version"] = GATEWAY_VERSION
    data.setdefault("queued_signatures", [])
    data.setdefault("history", [])
    return data


def _persist_state(root: Path, state: dict[str, Any]) -> None:
    normalized = dict(state)
    normalized["version"] = GATEWAY_VERSION
    atomic_write_json(root / STATE_JSON_REL, normalized)


def _scrub_params(params: dict[str, Any]) -> dict[str, Any]:
    scrubbed: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, str):
            scrubbed[key] = _compact(value, 160)
        elif isinstance(value, (int, float, bool)) or value is None:
            scrubbed[key] = value
        elif isinstance(value, list):
            scrubbed[key] = [_compact(item, 120) for item in value[:8]]
        else:
            scrubbed[key] = _compact(json.dumps(value, ensure_ascii=False, default=str), 200)
    return scrubbed


def _markdown_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*-?\s*([A-Za-z0-9_]+):\s*(.*?)\s*$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def _jsonl_summary(path: Path) -> tuple[int, str]:
    rows = 0
    last = ""
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                rows += 1
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(data, dict):
                    last = _safe_str(data.get("event_kind") or data.get("status"))
    except OSError:
        return 0, ""
    return rows, last


def _is_safe_relative(value: str) -> bool:
    text = _safe_str(value).replace("\\", "/").strip()
    return bool(text) and not text.startswith("/") and ".." not in text.split("/") and ":" not in text


def _read_json(path: Path, *, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def _read_text(path: Path, *, limit: int) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""
    return text if len(text) <= limit else text[-limit:]


def _hash_json(value: Any, *, length: int) -> str:
    return _hash_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str), length)


def _hash_text(value: Any, length: int = 16) -> str:
    return hashlib.sha256(_safe_str(value).encode("utf-8", errors="replace")).hexdigest()[:length]


def _compact(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    return text if len(text) <= limit else text[: max(0, limit - 3)] + "..."


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_token(value: Any) -> str:
    text = _safe_str(value).strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    return text.strip("_")[:80]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any = None) -> str:
    text = _safe_str(value).strip()
    if not text or text.lower() in {"none", "unknown", "null", "n/a", "na"}:
        return _now_iso()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return _now_iso()
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat(timespec="seconds")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run XinYu self action gateway.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--checked-at", default=None)
    parser.add_argument("--trigger", default="manual")
    parser.add_argument("--no-execute", action="store_true")
    parser.add_argument("--list-approvals", action="store_true")
    parser.add_argument("--approve", nargs="?", const="latest", default=None, metavar="QUEUE_ID")
    parser.add_argument("--deny", nargs="?", const="latest", default=None, metavar="QUEUE_ID")
    parser.add_argument("--approval-reason", default="")
    parser.add_argument("--execute-approved", nargs="?", const="next", default=None, metavar="QUEUE_ID")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.list_approvals:
        result = list_self_action_approvals(args.root)
    elif args.approve is not None:
        result = decide_self_action_approval(
            args.root,
            queue_id=args.approve,
            decision="approved",
            decided_at=args.checked_at,
            reason=args.approval_reason,
            execute=args.execute_approved is not None,
        )
    elif args.deny is not None:
        result = decide_self_action_approval(
            args.root,
            queue_id=args.deny,
            decision="denied",
            decided_at=args.checked_at,
            reason=args.approval_reason,
            execute=False,
        )
    elif args.execute_approved is not None:
        result = execute_approved_self_actions(
            args.root,
            queue_id=args.execute_approved,
            checked_at=args.checked_at,
        )
    else:
        result = run_self_action_gateway(
            args.root,
            checked_at=args.checked_at,
            trigger=args.trigger,
            execute_low_risk=not args.no_execute,
        )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status={result.get('status')}")
        if "selected_goal_id" in result:
            print(f"selected_goal_id={result.get('selected_goal_id')}")
            print(f"executed_action_count={result.get('executed_action_count')}")
            print(f"queued_approval_count={result.get('queued_approval_count')}")
        if "approval_queue" in result:
            queue = result.get("approval_queue") if isinstance(result.get("approval_queue"), dict) else {}
            print(f"pending_count={queue.get('pending_count', 0)}")
            print(f"approved_waiting_execution_count={queue.get('approved_waiting_execution_count', 0)}")
            print(f"latest_pending_queue_id={queue.get('latest_pending_queue_id', 'none')}")
        if "decision" in result:
            print(f"queue_id={result.get('queue_id')}")
            print(f"decision={result.get('decision')}")
            if isinstance(result.get("execution"), dict):
                print(f"execution_status={result['execution'].get('status')}")
                print(f"executed_count={result['execution'].get('executed_count')}")
        if "executed_count" in result:
            print(f"executed_count={result.get('executed_count')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
