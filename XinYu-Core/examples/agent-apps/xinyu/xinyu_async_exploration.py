from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_async_exploration_store import append_async_exploration_jsonl
from xinyu_async_exploration_store import read_async_exploration_report_text
from xinyu_async_exploration_store import read_async_exploration_text
from xinyu_async_exploration_store import write_async_exploration_text
from xinyu_dialogue_working_memory import load_dialogue_tail
from xinyu_visible_persona_voice import compose_async_exploration_outbox_message


STATE_REL = Path("memory/context/async_exploration_state.md")
TRACE_REL = Path("runtime/async_exploration_trace.jsonl")
CLOSURES_REL = Path("runtime/async_exploration_closures.jsonl")

RESUME_RE = re.compile(r"(?i)\b(?:resume_id|resume|继续|重试|放弃)\s*[:：#]?\s*(wait-\d{8}-[a-f0-9]{6,12})")
RETRY_MARKERS = ("继续", "重试", "retry", "resume", "再跑")
CANCEL_MARKERS = ("放弃", "取消", "不用了", "cancel", "stop")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


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
    return read_async_exploration_text(path)


def _write(path: Path, text: str) -> None:
    write_async_exploration_text(path, text)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    append_async_exploration_jsonl(path, row)


def _field(text: str, name: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^\s*-\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        match = re.search(rf"(?m)^\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        return default
    return _compact(match.group(1), limit=320, default=default)


def _owner_user_id(payload: dict[str, Any] | None) -> str:
    payload = payload if isinstance(payload, dict) else {}
    return _compact(payload.get("user_id"), limit=64, default="")


def _path_label(path_text: str) -> str:
    text = _safe_str(path_text).strip()
    if not text:
        return "none"
    try:
        return Path(text).name or "none"
    except Exception:
        return "none"


def _tail_summary(tail: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for item in tail[-10:]:
        role = _safe_str(item.get("role")).strip()
        content = _compact(item.get("content"), limit=360, default="")
        if role and content:
            entry = {"role": role, "content": content}
            recorded = _safe_str(item.get("recorded_at")).strip()
            if recorded:
                entry["recorded_at"] = _compact(recorded, limit=80, default="none")
            items.append(entry)
    return items


def _render_state(fields: dict[str, str]) -> str:
    return f"""---
title: Async Exploration State
memory_type: async_exploration_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_async_exploration
updated_at: {fields['updated_at']}
status: active
tags: [async, codex, wait-to-think, suspension]
---

# Async Exploration State

## Current Suspension
- resume_id: {fields['resume_id']}
- updated_at: {fields['updated_at']}
- status: {fields['status']}
- session_key: {fields['session_key']}
- user_id: {fields['user_id']}
- delegation_reason: {fields['delegation_reason']}
- expected_format: {fields['expected_format']}
- execution_plan: {fields.get('execution_plan', 'none')}
- task_summary: {fields['task_summary']}
- codex_job_id: {fields['codex_job_id']}
- report_label: {fields['report_label']}
- failure_kind: {fields['failure_kind']}
- result_quality: {fields['result_quality']}
- sanitized_summary: {fields['sanitized_summary']}
- owner_intervention: {fields.get('owner_intervention', 'none')}
- owner_visible_resume_hint: {fields['owner_visible_resume_hint']}

## Recovery Rules
- raw_stdout_stderr_to_ai: blocked
- prompt_injection_material_to_ai: blocked
- resume_requires_owner_instruction_after_failure: true
- default_after_failure: preserve_snapshot_and_continue_chat
- retry_scope: owner may resume with narrower instruction by mentioning resume_id
"""


def create_async_exploration_closure(
    root: Path,
    payload: dict[str, Any] | None = None,
    *,
    session_key: str,
    user_text: str,
    draft_reply: str,
    task_text: str,
    delegation_reason: str = "",
    expected_format: str = "sanitized summary plus final answer boundary",
    execution_plan: str = "",
    created_at: str | None = None,
) -> dict[str, Any]:
    observed = created_at or _now_iso()
    root = root.resolve()
    resume_id = "wait-" + datetime.now().astimezone().strftime("%Y%m%d") + "-" + _hash(
        f"{observed}|{session_key}|{user_text}|{time.time_ns()}",
        8,
    )
    tail = _tail_summary(load_dialogue_tail(root, session_key, max_entries=10, include_timestamps=True))
    closure = {
        "resume_id": resume_id,
        "created_at": observed,
        "updated_at": observed,
        "status": "delegated_to_codex",
        "session_key": session_key,
        "user_id": _owner_user_id(payload),
        "owner_message": _compact(user_text, limit=800),
        "draft_reply": _compact(draft_reply, limit=800),
        "delegation_reason": _compact(delegation_reason or task_text, limit=500),
        "expected_format": _compact(expected_format, limit=240),
        "execution_plan": _compact(execution_plan, limit=1200),
        "task_text": _compact(task_text, limit=1800),
        "last_n_messages": tail,
        "codex_job_id": "none",
        "report_path": "",
        "failure_kind": "none",
        "result_quality": "pending",
        "sanitized_summary": "none",
    }
    _append_jsonl(root / CLOSURES_REL, closure)
    fields = {
        "resume_id": resume_id,
        "updated_at": observed,
        "status": "delegated_to_codex",
        "session_key": session_key,
        "user_id": closure["user_id"],
        "delegation_reason": closure["delegation_reason"],
        "expected_format": closure["expected_format"],
        "execution_plan": closure["execution_plan"],
        "task_summary": _compact(task_text, limit=220),
        "codex_job_id": "none",
        "report_label": "none",
        "failure_kind": "none",
        "result_quality": "pending",
        "sanitized_summary": "none",
        "owner_visible_resume_hint": f"resume_id: {resume_id}",
    }
    _write(root / STATE_REL, _render_state(fields))
    _append_jsonl(root / TRACE_REL, {"event_kind": "created", **closure})
    return {
        "created": True,
        "resume_id": resume_id,
        "user_id": closure["user_id"],
        "transition_message": "我这句不硬答了，我去后台验证一下，等结果出来再接着说。",
        "notes": [f"async_exploration_created:{resume_id}"],
    }


def _sanitized_report_summary(report_path: str, *, limit: int = 420) -> tuple[str, str]:
    path = Path(report_path) if report_path else Path()
    if not report_path:
        return "missing_report", "none"
    read_status, text = read_async_exploration_report_text(path)
    if read_status == "missing_report":
        return "missing_report", "none"
    if read_status == "unreadable_report":
        return "unreadable_report", "none"
    if not text.strip():
        return "empty_report", "none"
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line in {"---", "```", "```text"}:
            continue
        if line.startswith(("#", "title:", "created_at:", "generated_at:", "status:")):
            continue
        if re.search(r"(?i)(authorization|bearer|api[_-]?key|token\s*[:=]|sk-[a-z0-9_-]{8,})", line):
            continue
        if re.search(r"(?i)([a-z]:\\|/users/|/home/|\\\\)", line):
            line = re.sub(r"(?i)([a-z]:\\[^\s]+|/users/\S+|/home/\S+|\\\\\S+)", "<local_path>", line)
        line = _compact(line.strip("- "), limit=180, default="")
        if line:
            lines.append(line)
        if len(lines) >= 3:
            break
    summary = "；".join(lines)
    if not summary:
        return "low_signal_report", "none"
    return "usable_partial" if len(summary) <= limit else "usable_partial", _compact(summary, limit=limit)


def update_async_exploration_from_codex(
    root: Path,
    *,
    resume_id: str,
    result: Any | None,
    error: str = "",
    owner_intervention: str = "",
    updated_at: str | None = None,
) -> dict[str, Any]:
    observed = updated_at or _now_iso()
    root = root.resolve()
    report_path = _safe_str(getattr(result, "report_path", "")) if result is not None else ""
    report_label = _path_label(report_path)
    timed_out = bool(getattr(result, "timed_out", False)) if result is not None else False
    accepted = bool(getattr(result, "accepted", False)) if result is not None else False
    exit_code = getattr(result, "exit_code", None) if result is not None else None
    if error:
        failure_kind = "bridge_error"
        result_quality = "failed"
        sanitized = _compact(error, limit=260)
    elif timed_out:
        failure_kind = "codex_timeout"
        result_quality = "failed"
        sanitized = "Codex timed out; no verified final answer was produced."
    elif not accepted:
        failure_kind = "codex_failed" if exit_code is not None else "codex_not_accepted"
        result_quality = "failed"
        sanitized = f"Codex did not complete successfully; exit_code={exit_code if exit_code is not None else 'unknown'}."
    else:
        failure_kind, sanitized = _sanitized_report_summary(report_path)
        result_quality = "usable_partial" if failure_kind == "usable_partial" else "failed"
    status = "codex_result_ready" if result_quality == "usable_partial" else "failed_snapshot_saved"
    previous_state = _read(root / STATE_REL)
    fields = {
        "resume_id": resume_id,
        "updated_at": observed,
        "status": status,
        "session_key": _field(previous_state, "session_key", "none"),
        "user_id": _field(previous_state, "user_id", "none"),
        "delegation_reason": _field(previous_state, "delegation_reason", "none"),
        "expected_format": _field(previous_state, "expected_format", "none"),
        "task_summary": _field(previous_state, "task_summary", "none"),
        "codex_job_id": _safe_str(getattr(result, "request_path", "") or "none") if result is not None else "none",
        "report_label": report_label,
        "failure_kind": failure_kind,
        "result_quality": result_quality,
        "sanitized_summary": sanitized,
        "owner_intervention": _compact(owner_intervention, limit=240),
        "owner_visible_resume_hint": f"resume_id: {resume_id}",
    }
    _write(root / STATE_REL, _render_state(fields))
    _append_jsonl(
        root / TRACE_REL,
        {
            "event_kind": "codex_result",
            "resume_id": resume_id,
            "updated_at": observed,
            "status": status,
            "failure_kind": failure_kind,
            "result_quality": result_quality,
            "report_label": report_label,
            "owner_intervention": _compact(owner_intervention, limit=240),
        },
    )
    return {
        "updated": True,
        "resume_id": resume_id,
        "status": status,
        "failure_kind": failure_kind,
        "result_quality": result_quality,
        "sanitized_summary": sanitized,
        "report_label": report_label,
        "owner_intervention": _compact(owner_intervention, limit=240),
        "notes": [f"async_exploration_result:{status}:{failure_kind}"],
    }


def async_exploration_outbox_message(update: dict[str, Any]) -> str:
    return compose_async_exploration_outbox_message(update)


def parse_resume_instruction(text: str) -> dict[str, str]:
    match = RESUME_RE.search(text or "")
    if not match:
        return {}
    resume_id = match.group(1)
    lowered = text.lower()
    action = "cancel" if any(marker in lowered for marker in CANCEL_MARKERS) else "retry"
    if any(marker in lowered for marker in RETRY_MARKERS):
        action = "retry"
    instruction = re.sub(re.escape(resume_id), "", text, flags=re.I).strip()
    return {"resume_id": resume_id, "action": action, "instruction": _compact(instruction, limit=360)}


def build_async_exploration_prompt_block(root: Path, *, limit: int = 1200) -> str:
    state = _read(root / STATE_REL)
    if not state:
        return ""
    status = _field(state, "status", "none")
    if status in {"none", "unknown"}:
        return ""
    lines = [
        "async exploration sidecar:",
        "facts:",
        f"- resume_id: {_field(state, 'resume_id', 'none')}",
        f"- status: {status}",
        f"- delegation_reason: {_field(state, 'delegation_reason', 'none')}",
        f"- execution_plan: {_field(state, 'execution_plan', 'none')}",
        f"- result_quality: {_field(state, 'result_quality', 'none')}",
        f"- failure_kind: {_field(state, 'failure_kind', 'none')}",
        f"- sanitized_summary: {_field(state, 'sanitized_summary', 'none')}",
        f"- owner_intervention: {_field(state, 'owner_intervention', 'none')}",
        "truth_rules:",
        "- if result_quality is failed, say the task did not complete; do not infer a final answer from missing output",
        "- if result_quality is usable_partial, only state what the sanitized summary supports and keep unknowns open",
        "- if owner_intervention is present, treat the result as owner-guided recovery, not autonomous completion",
        "expression_rules:",
        "- never print raw logs, stdout, stderr, state names, field names, hashes, sidecar/ticket/trace wording, or file paths",
        "- natural owner-facing wording may say: 刚才是你让我缩小范围继续查的，所以我只确认了这一块",
        "- do not turn the recovery into a report unless owner asks for system/runtime details",
        "reply_task:",
        "- reconnect to the suspended conversation and give the next useful answer",
        "- if failed, say it did not complete and offer retry/abandon choices using the resume_id only when useful",
    ]
    return "\n".join(lines)[:limit].rstrip()
