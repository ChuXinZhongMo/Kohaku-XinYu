from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_self_code_approval_store import append_self_code_approval_trace
from xinyu_self_code_approval_store import read_self_code_approval_text
from xinyu_self_code_approval_store import write_self_code_approval_text


STATE_REL = Path("memory/context/self_code_approval_state.md")
TRACE_REL = Path("runtime/self_code_approval_trace.jsonl")
PROACTIVE_REQUEST_REL = Path("memory/context/proactive_request_state.md")

REQUEST_FOCUS_KIND = "self_code_approval"
APPROVAL_STATUSES = {"ready", "claimed", "sent", "pending_owner_reply", "candidate_only"}
APPROVAL_MARKERS = (
    "同意",
    "允许",
    "授权",
    "准许",
    "可以",
    "开始",
    "动手",
    "直接改",
    "去改",
    "进行修改",
    "可以修改",
    "批准",
    "approved",
    "approve",
    "yes",
    "ok",
)
DENIAL_MARKERS = (
    "不同意",
    "不允许",
    "别改",
    "不要改",
    "先别改",
    "拒绝",
    "取消",
    "不批准",
    "stop",
    "cancel",
    "no",
)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _timestamp_or_now_iso(value: Any) -> str:
    text = _safe_str(value).strip()
    if not text:
        return _now_iso()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return _now_iso()
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat()


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _compact(value: Any, *, limit: int = 220, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:length]


def _read(path: Path) -> str:
    return read_self_code_approval_text(path)


def _write(path: Path, text: str) -> None:
    write_self_code_approval_text(path, text)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    append_self_code_approval_trace(path, row)


def _field(text: str, name: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^\s*-\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        match = re.search(rf"(?m)^\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        return default
    return _compact(match.group(1), limit=320, default=default)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    lowered = _safe_str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _owner_private(payload: dict[str, Any] | None) -> bool:
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    is_owner = _as_bool(payload.get("is_owner_user") or metadata.get("is_owner_user"), default=False)
    group_id = _safe_str(payload.get("group_id")).strip()
    message_type = _safe_str(payload.get("message_type")).strip().lower()
    return is_owner and not group_id and not message_type.startswith("group")


def _contains_marker(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    compact = re.sub(r"\s+", "", lowered)
    return any(marker.lower() in lowered or marker.lower().replace(" ", "") in compact for marker in markers)


def _approval_decision(text: str) -> str:
    if _contains_marker(text, DENIAL_MARKERS):
        return "denied"
    if _contains_marker(text, APPROVAL_MARKERS):
        return "approved"
    return "none"


def _active_request_from_proactive(root: Path) -> dict[str, str]:
    state = _read(root / PROACTIVE_REQUEST_REL)
    if _field(state, "focus_kind", "none") != REQUEST_FOCUS_KIND:
        return {}
    status = _field(state, "status", "none")
    if status not in APPROVAL_STATUSES:
        return {}
    if _field(state, "requested_action", "none") != "owner_permission":
        return {}
    return {
        "request_id": _field(state, "request_id", "none"),
        "status": status,
        "kind": _field(state, "kind", "permission"),
        "focus_label": _field(state, "focus_label", "self_code_approval"),
        "evidence_label": _field(state, "evidence_label", "self-code approval request"),
        "evidence_hash": _field(state, "evidence_hash", "none"),
        "concrete_question": _field(state, "concrete_question", "none"),
        "after_owner_replies": _field(state, "after_owner_replies", "none"),
    }


def active_self_code_approval_request(root: Path) -> dict[str, str]:
    return _active_request_from_proactive(root)


def _render_state(fields: dict[str, str]) -> str:
    value = lambda key, default="none": fields.get(key, default)
    return f"""---
title: Self Code Approval State
memory_type: self_code_approval_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_self_code_approval
updated_at: {value('updated_at')}
status: active
tags: [self-code, approval, codex, owner-private]
---

# Self Code Approval State

## Current Approval
- approval_id: {value('approval_id')}
- updated_at: {value('updated_at')}
- status: {value('status')}
- approval_route: {value('approval_route', 'pending_qq_application')}
- proactive_request_id: {value('proactive_request_id')}
- request_status: {value('request_status')}
- evidence_hash: {value('evidence_hash')}
- owner_decision: {value('owner_decision')}
- owner_message_summary: {value('owner_message_summary')}
- approval_scope: {value('approval_scope')}
- codex_task_summary: {value('codex_task_summary')}
- execution_job_id: {value('execution_job_id')}
- watchdog_snapshot_id: {value('watchdog_snapshot_id')}
- watchdog_manifest_path: {value('watchdog_manifest_path')}

## Rules
- owner_private_required: true
- approval_is_one_time: true
- require_prior_qq_application: {value('require_prior_qq_application', 'true')}
- direct_owner_private_grant: explicit_owner_private_request_allowed_once
- direct_silent_self_edit: blocked
- allowed_executor: Codex bounded local delegate
- write_scope: XinYu app code and focused tests only
- stable_memory_write: blocked unless the patch only updates owner-approved policy text
- report_back_to_owner: required
"""


def _default_codex_task(request: dict[str, str], *, owner_text: str, session_key: str, reply: str) -> str:
    evidence = request.get("evidence_label") or "self-code approval request"
    request_id = request.get("request_id") or "unknown"
    question = request.get("concrete_question") or "none"
    return "\n".join(
        [
            "Owner approved XinYu's prior QQ self-code application. This is a one-time bounded approval.",
            f"Approval source proactive_request_id: {request_id}",
            f"Approval evidence: {evidence}",
            f"Original application question: {question}",
            f"Owner approval message: {owner_text}",
            f"XinYu draft around approval turn: {reply}",
            f"Session: {session_key}",
            (
                "Task: inspect the XinYu app and implement one focused, reversible patch that improves "
                "the approved runtime problem. Prefer continuity handoff, uncertainty/pause handling, "
                "self-thought-to-proactive approval flow, or mechanical voice repair if those are implicated. "
                "If the owner criticized XinYu's self-code/code modification ability, focus on the self-code "
                "trigger, Codex delegation prompt, watchdog, validation, or report-back path. Do not stop at "
                "a report when a bounded code patch is possible. "
                "Modify only files under examples/agent-apps/xinyu unless a directly related test under that app "
                "is required. Add or update focused tests/smokes and run the relevant checks. Do not touch secrets, "
                "credentials, browser/session files, unrelated projects, public Git metadata, or stable personality/core "
                "memory except for owner-approved policy wording. If a conflicting edit or running Codex job blocks the "
                "patch, report the blocker instead of guessing."
            ),
        ]
    )


def _direct_codex_task(*, owner_text: str, session_key: str, reply: str) -> str:
    return "\n".join(
        [
            "Owner directly requested or authorized XinYu to modify her own code in QQ private chat.",
            "This is a one-time direct owner-private approval, not standing permission.",
            f"Owner direct instruction: {owner_text}",
            f"XinYu draft around direct instruction: {reply}",
            f"Session: {session_key}",
            (
                "Task: inspect the XinYu app and implement the concrete code change requested by the owner. "
                "If the request is broad, choose one focused, reversible patch that materially improves the "
                "stated XinYu runtime behavior instead of asking again or only describing intent. "
                "If the owner says XinYu's self-code/code modification ability is weak, strengthen the actual "
                "self-code execution path: owner-private intent detection, Codex delegation prompt, watchdog "
                "snapshot/reporting, and focused tests. Do not answer with only analysis when a bounded patch is possible. "
                "Modify only files under examples/agent-apps/xinyu unless a directly related focused test under that app is "
                "required. Add or update focused tests/smokes and run the relevant checks. Do not touch secrets, "
                "credentials, browser/session files, unrelated projects, public Git metadata, or stable personality/core "
                "memory except for owner-approved policy wording. If a conflicting edit or running Codex job blocks the "
                "patch, report the blocker instead of pretending to proceed."
            ),
        ]
    )


def consume_self_code_approval(
    root: Path,
    payload: dict[str, Any] | None = None,
    *,
    owner_text: str,
    session_key: str,
    reply: str = "",
    observed_at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    observed = observed_at or _now_iso()
    if not _owner_private(payload):
        return {"approved": False, "denied": False, "notes": ["self_code_approval_not_owner_private"]}
    request = _active_request_from_proactive(root)
    if not request:
        return {"approved": False, "denied": False, "notes": ["self_code_approval_no_pending_request"]}

    decision = _approval_decision(owner_text)
    if decision == "none":
        return {"approved": False, "denied": False, "notes": ["self_code_approval_no_decision_marker"]}

    approval_id = "selfcode-approval-" + _hash(
        f"{observed}|{request.get('request_id')}|{owner_text}|{time.time_ns()}",
        18,
    )
    task = _default_codex_task(request, owner_text=owner_text, session_key=session_key, reply=reply)
    fields = {
        "approval_id": approval_id,
        "updated_at": _timestamp_or_now_iso(observed),
        "status": "denied" if decision == "denied" else "approved_once",
        "approval_route": "pending_qq_application",
        "proactive_request_id": request.get("request_id", "none"),
        "request_status": request.get("status", "none"),
        "evidence_hash": request.get("evidence_hash", "none"),
        "owner_decision": decision,
        "owner_message_summary": _compact(owner_text, limit=180),
        "approval_scope": "one_time_bounded_xinyu_app_patch_via_codex" if decision == "approved" else "none",
        "codex_task_summary": _compact(task, limit=260),
        "execution_job_id": "none",
        "watchdog_snapshot_id": "none",
        "watchdog_manifest_path": "none",
        "require_prior_qq_application": "true",
    }
    _write(root / STATE_REL, _render_state(fields))
    _append_jsonl(
        root / TRACE_REL,
        {
            "approval_id": approval_id,
            "observed_at": _timestamp_or_now_iso(observed),
            "decision": decision,
            "proactive_request_id": request.get("request_id", "none"),
            "evidence_hash": request.get("evidence_hash", "none"),
        },
    )
    if decision == "denied":
        return {
            "approved": False,
            "denied": True,
            "approval_id": approval_id,
            "notes": ["self_code_approval_denied"],
        }
    return {
        "approved": True,
        "denied": False,
        "approval_id": approval_id,
        "task_text": task,
        "notes": ["self_code_approval_consumed_once"],
    }


def create_direct_self_code_approval(
    root: Path,
    payload: dict[str, Any] | None = None,
    *,
    owner_text: str,
    session_key: str,
    reply: str = "",
    observed_at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    observed = observed_at or _now_iso()
    if not _owner_private(payload):
        return {"approved": False, "denied": False, "notes": ["self_code_direct_grant_not_owner_private"]}
    approval_id = "selfcode-direct-" + _hash(
        f"{observed}|direct-owner-private|{owner_text}|{time.time_ns()}",
        18,
    )
    task = _direct_codex_task(owner_text=owner_text, session_key=session_key, reply=reply)
    fields = {
        "approval_id": approval_id,
        "updated_at": _timestamp_or_now_iso(observed),
        "status": "approved_once",
        "approval_route": "direct_owner_private_qq_request",
        "proactive_request_id": "none",
        "request_status": "direct_owner_private",
        "evidence_hash": "sha256:" + _hash(owner_text, 16),
        "owner_decision": "approved",
        "owner_message_summary": _compact(owner_text, limit=180),
        "approval_scope": "one_time_direct_owner_private_xinyu_app_patch_via_codex",
        "codex_task_summary": _compact(task, limit=260),
        "execution_job_id": "none",
        "watchdog_snapshot_id": "none",
        "watchdog_manifest_path": "none",
        "require_prior_qq_application": "false",
    }
    _write(root / STATE_REL, _render_state(fields))
    _append_jsonl(
        root / TRACE_REL,
        {
            "approval_id": approval_id,
            "observed_at": _timestamp_or_now_iso(observed),
            "decision": "approved",
            "approval_route": "direct_owner_private_qq_request",
            "evidence_hash": fields["evidence_hash"],
        },
    )
    return {
        "approved": True,
        "denied": False,
        "approval_id": approval_id,
        "task_text": task,
        "notes": ["self_code_direct_owner_private_grant_consumed_once"],
    }


def mark_self_code_execution_scheduled(
    root: Path,
    *,
    approval_id: str,
    job_id: str,
    watchdog_snapshot_id: str = "none",
    watchdog_manifest_path: str = "none",
    observed_at: str | None = None,
) -> None:
    existing = _read(root / STATE_REL)
    if not existing:
        return
    observed = observed_at or _now_iso()
    fields = {
        "approval_id": _field(existing, "approval_id", approval_id),
        "updated_at": observed,
        "status": "executing",
        "approval_route": _field(existing, "approval_route", "pending_qq_application"),
        "proactive_request_id": _field(existing, "proactive_request_id", "none"),
        "request_status": _field(existing, "request_status", "none"),
        "evidence_hash": _field(existing, "evidence_hash", "none"),
        "owner_decision": _field(existing, "owner_decision", "approved"),
        "owner_message_summary": _field(existing, "owner_message_summary", "none"),
        "approval_scope": _field(existing, "approval_scope", "one_time_bounded_xinyu_app_patch_via_codex"),
        "codex_task_summary": _field(existing, "codex_task_summary", "none"),
        "execution_job_id": _compact(job_id, limit=80),
        "watchdog_snapshot_id": _compact(
            watchdog_snapshot_id if watchdog_snapshot_id != "none" else _field(existing, "watchdog_snapshot_id", "none"),
            limit=100,
        ),
        "watchdog_manifest_path": _compact(
            watchdog_manifest_path
            if watchdog_manifest_path != "none"
            else _field(existing, "watchdog_manifest_path", "none"),
            limit=500,
        ),
        "require_prior_qq_application": _field(existing, "require_prior_qq_application", "true"),
    }
    _write(root / STATE_REL, _render_state(fields))
    _append_jsonl(
        root / TRACE_REL,
        {
            "approval_id": fields["approval_id"],
            "observed_at": _timestamp_or_now_iso(observed),
            "event_kind": "execution_scheduled",
            "job_id": fields["execution_job_id"],
            "watchdog_snapshot_id": fields["watchdog_snapshot_id"],
        },
    )


def build_self_code_approval_prompt_block(root: Path, *, limit: int = 1000) -> str:
    request = _active_request_from_proactive(root)
    state = _read(root / STATE_REL)
    lines: list[str] = []
    if request:
        lines.extend(
            [
                "self-code approval sidecar:",
                "- pending_application: true",
                f"- proactive_request_id: {request.get('request_id', 'none')}",
                f"- request_status: {request.get('status', 'none')}",
                f"- evidence: {request.get('evidence_label', 'none')}",
                "- approval_rule: only an owner-private approval to this pending QQ application may start self-code modification",
                "- direct_grant_without_pending_application: allowed only when the current owner-private message explicitly asks XinYu to modify her own code",
            ]
        )
    elif state:
        status = _field(state, "status", "none")
        lines.extend(
            [
                "self-code approval sidecar:",
                f"- status: {status}",
                f"- latest_approval_id: {_field(state, 'approval_id', 'none')}",
                f"- approval_route: {_field(state, 'approval_route', 'pending_qq_application')}",
                f"- execution_job_id: {_field(state, 'execution_job_id', 'none')}",
                f"- watchdog_snapshot_id: {_field(state, 'watchdog_snapshot_id', 'none')}",
                "- approval_rule: one-time approvals do not persist after execution",
            ]
        )
    return "\n".join(lines)[:limit].rstrip()
