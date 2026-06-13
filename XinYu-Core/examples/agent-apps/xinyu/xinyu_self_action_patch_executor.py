from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_codex_delegate import preview_codex_delegate_paths, run_codex_delegate
from xinyu_self_action_patch_executor_store import append_self_action_patch_executor_trace
from xinyu_self_action_patch_executor_store import read_self_action_patch_executor_json
from xinyu_self_action_patch_executor_store import read_self_action_patch_executor_text
from xinyu_self_action_patch_executor_store import write_self_action_patch_executor_json
from xinyu_self_action_patch_executor_store import write_self_action_patch_executor_text
from xinyu_self_action_gateway import APPROVAL_HANDOFF_REL
from xinyu_self_code_approval import mark_self_code_execution_scheduled
from xinyu_self_code_watchdog import create_self_code_snapshot


EXECUTOR_VERSION = 1
STATE_JSON_REL = Path("runtime/self_action_patch_executor/state.json")
STATE_MD_REL = Path("memory/context/self_action_patch_executor_state.md")
TASK_MD_REL = Path("memory/context/self_action_patch_executor_task.md")
TRACE_REL = Path("runtime/self_action_patch_executor/trace.jsonl")
TASK_DIR_REL = Path("runtime/self_action_patch_executor/tasks")

EXECUTION_LEVELS = {"prepare", "schedule_codex", "execute_codex"}
PATCH_ACTION_KINDS = {"self_code_patch_request"}
PATCH_APPROVAL_SCOPES = {"focused_xinyu_app_patch", "replay_fixture_or_test_patch"}
CODEX_WINDOW_TITLE = "Xinyu codex"

_FIELD_RE = re.compile(r"(?m)^\s*-\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")


def run_self_action_patch_executor(
    root: Path,
    *,
    checked_at: str | None = None,
    execution_level: str = "prepare",
    allow_codex: bool = False,
    timeout_seconds: int = 1800,
    force: bool = False,
    write_state: bool = True,
) -> dict[str, Any]:
    root = Path(root)
    checked_at = _timestamp_or_now_iso(checked_at)
    execution_level = _safe_token(execution_level) or "prepare"
    if execution_level not in EXECUTION_LEVELS:
        execution_level = "prepare"

    handoff = _load_handoff(root)
    if not handoff:
        result = _blocked_result(checked_at, "no_self_action_handoff", execution_level)
        if write_state:
            _persist_result(root, result)
        return result

    action_kind = _safe_str(handoff.get("action_kind"))
    if action_kind not in PATCH_ACTION_KINDS:
        result = _blocked_result(checked_at, "handoff_not_patch_action", execution_level, handoff=handoff)
        if write_state:
            _persist_result(root, result)
        return result
    approval_scope = _safe_str(handoff.get("approval_scope"))
    if approval_scope not in PATCH_APPROVAL_SCOPES:
        result = _blocked_result(checked_at, "handoff_not_code_patch_scope", execution_level, handoff=handoff)
        if write_state:
            _persist_result(root, result)
        return result

    approval_id = _safe_str(handoff.get("approval_id"), "unknown")
    queue_id = _safe_str(handoff.get("queue_id"), "unknown")
    state = _read_json(root / STATE_JSON_REL, default={})
    existing_codex_status = _safe_str(state.get("last_codex_status")) if isinstance(state, dict) else ""
    if (
        not force
        and execution_level in {"schedule_codex", "execute_codex"}
        and isinstance(state, dict)
        and _safe_str(state.get("last_approval_id")) == approval_id
        and existing_codex_status in {"scheduled", "finished", "timed_out", "failed"}
    ):
        reason = "approval_already_scheduled" if existing_codex_status == "scheduled" else "approval_already_executed"
        result = _blocked_result(checked_at, reason, execution_level, handoff=handoff)
        if write_state:
            _persist_result(root, result)
        return result

    task = _build_patch_task(handoff, checked_at=checked_at)
    task_paths = _write_patch_task(root, task)

    codex: dict[str, Any] = {"status": "not_requested"}
    watchdog: dict[str, Any] = {}
    status = "prepared"
    notes = ["patch_task_prepared"]

    if execution_level in {"schedule_codex", "execute_codex"}:
        if not allow_codex:
            status = "blocked"
            notes.append("codex_execution_not_allowed")
            codex = {"status": "blocked", "reason": "allow_codex_false"}
        else:
            watchdog = create_self_code_snapshot(
                root,
                approval_id=approval_id,
                reason="self_action_patch_executor_before_codex_patch",
                observed_at=_timestamp_or_now_iso(checked_at),
            )
            task = _with_watchdog_block(task, watchdog)
            task_paths = _write_patch_task(root, task)
            payload = _codex_payload(
                task,
                handoff=handoff,
                timeout_seconds=timeout_seconds,
                checked_at=checked_at,
                background=execution_level == "schedule_codex",
            )
            if execution_level == "schedule_codex":
                paths = preview_codex_delegate_paths(root, payload)
                codex = {
                    "status": "scheduled",
                    "job_id": _safe_str(paths.get("job_id") or payload.get("job_id")),
                    "request_path": _safe_str(paths.get("request_path")),
                    "workspace_path": _safe_str(paths.get("workspace_path")),
                    "report_path": _safe_str(paths.get("report_path")),
                    "last_message_path": _safe_str(paths.get("last_message_path")),
                }
                status = "codex_scheduled"
                notes.extend(["codex_delegate_scheduled", f"codex_status:{codex['status']}"])
                try:
                    mark_self_code_execution_scheduled(
                        root,
                        approval_id=approval_id,
                        job_id=_safe_str(codex.get("request_path") or codex.get("report_path")),
                        watchdog_snapshot_id=_safe_str(watchdog.get("snapshot_id"), "none"),
                        watchdog_manifest_path=_safe_str(watchdog.get("manifest_path"), "none"),
                        observed_at=_timestamp_or_now_iso(checked_at),
                    )
                except Exception as exc:
                    notes.append(f"self_code_approval_mark_error:{type(exc).__name__}")
            else:
                result = run_codex_delegate(root, payload)
                codex = _codex_result(result)
                status = _status_from_codex(codex)
                notes.extend(["codex_delegate_invoked", f"codex_status:{codex['status']}"])
                try:
                    mark_self_code_execution_scheduled(
                        root,
                        approval_id=approval_id,
                        job_id=_safe_str(codex.get("request_path") or codex.get("report_path")),
                        watchdog_snapshot_id=_safe_str(watchdog.get("snapshot_id"), "none"),
                        watchdog_manifest_path=_safe_str(watchdog.get("manifest_path"), "none"),
                        observed_at=_timestamp_or_now_iso(checked_at),
                    )
                except Exception as exc:
                    notes.append(f"self_code_approval_mark_error:{type(exc).__name__}")

    result = {
        "accepted": status not in {"blocked"},
        "status": status,
        "checked_at": checked_at,
        "execution_level": execution_level,
        "queue_id": queue_id,
        "approval_id": approval_id,
        "goal_id": _safe_str(handoff.get("goal_id")),
        "action_kind": action_kind,
        "approval_scope": _safe_str(handoff.get("approval_scope")),
        "task_id": task["task_id"],
        "task_path": task_paths["json"],
        "task_markdown_path": task_paths["markdown"],
        "codex": codex,
        "watchdog": watchdog,
        "notes": notes,
    }
    if execution_level == "schedule_codex" and status == "codex_scheduled":
        result["codex_payload"] = payload
    if write_state:
        _persist_result(root, result)
    return result


def _load_handoff(root: Path) -> dict[str, str]:
    text = _read_text(root / APPROVAL_HANDOFF_REL, limit=12000)
    if not text:
        return {}
    fields = _markdown_fields(text)
    return {
        "queue_id": _safe_str(fields.get("queue_id")),
        "approval_id": _safe_str(fields.get("approval_id")),
        "goal_id": _safe_str(fields.get("goal_id")),
        "action_kind": _safe_str(fields.get("action_kind")),
        "approval_scope": _safe_str(fields.get("approval_scope")),
        "execution_mode": _safe_str(fields.get("execution_mode")),
        "next_executor": _safe_str(fields.get("next_executor")),
    }


def _build_patch_task(handoff: dict[str, str], *, checked_at: str) -> dict[str, Any]:
    approval_id = _safe_str(handoff.get("approval_id"), "unknown")
    queue_id = _safe_str(handoff.get("queue_id"), "unknown")
    task_id = "selfaction-patch-" + _hash_json(
        {
            "approval_id": approval_id,
            "queue_id": queue_id,
            "action_kind": handoff.get("action_kind"),
        },
        length=16,
    )
    task_text = "\n".join(
        [
            f"Self-code approval id: {approval_id}",
            "Owner-approved Self Action Gateway patch executor task.",
            f"Gateway queue id: {queue_id}",
            f"Goal id: {_safe_str(handoff.get('goal_id'), 'none')}",
            f"Action kind: {_safe_str(handoff.get('action_kind'), 'none')}",
            f"Approval scope: {_safe_str(handoff.get('approval_scope'), 'none')}",
            "",
            "Task:",
            "- Inspect the current XinYu app state and choose one focused, reversible code patch.",
            "- Prefer the Self Action Gateway, goal ecology, outcome observer, or tests if they are the implicated surface.",
            "- If no safe patch is justified, write a report explaining why and do not edit files.",
            "",
            "Allowed scope:",
            "- examples/agent-apps/xinyu Python code and tests only.",
            "- Runtime state, generated task files, and watchdog snapshot files may be written as evidence.",
            "",
            "Forbidden:",
            "- Do not send QQ/outward messages.",
            "- Do not rewrite stable memory, owner relationship memory, secrets, credentials, or local env files.",
            "- Do not edit outside examples/agent-apps/xinyu.",
            "- Do not run destructive file operations.",
            "",
            "Verification:",
            "- Run the narrowest relevant pytest or smoke check.",
            "- Report changed files, verification commands, and remaining risks.",
            "",
            "Self-code implementation mode:",
            "- This task has owner-private self-code approval; do not reduce it to research-only output.",
            "- Inspect the implicated modules, make one bounded patch when safe, and keep edits reversible.",
            "- If a dirty file conflict or running Codex job blocks the patch, write the blocker and do not fake completion.",
        ]
    )
    return {
        "version": EXECUTOR_VERSION,
        "task_id": task_id,
        "created_at": _timestamp_or_now_iso(checked_at),
        "handoff": dict(handoff),
        "task_text": task_text,
        "allowed_scope": "examples/agent-apps/xinyu code and tests only",
        "forbidden": [
            "outward_send",
            "stable_memory_rewrite",
            "secret_reading",
            "outside_xinyu_app_edit",
            "destructive_file_operation",
        ],
    }


def _with_watchdog_block(task: dict[str, Any], watchdog: dict[str, Any]) -> dict[str, Any]:
    updated = dict(task)
    manifest_path = _safe_str(watchdog.get("manifest_path"), "none")
    snapshot_id = _safe_str(watchdog.get("snapshot_id"), "none")
    restart_command = (
        "powershell -NoProfile -ExecutionPolicy Bypass -File .\\start_xinyu_core_bridge.ps1 "
        f"-ForceRestart -SelfCodeSnapshotPath \"{manifest_path}\" -HealthTimeoutSeconds 60"
    )
    watchdog_block = "\n".join(
        [
            "",
            "Self-code watchdog:",
            f"- snapshot_id: {snapshot_id}",
            f"- snapshot_manifest: {manifest_path}",
            "- before changing files, keep this snapshot unchanged.",
            "- after implementing and testing the patch, reload Core through the PowerShell health gate.",
            f"- reload_command: {restart_command}",
            "- if the health gate fails, restore from the snapshot instead of continuing.",
        ]
    )
    updated["watchdog"] = dict(watchdog)
    updated["task_text"] = _safe_str(updated.get("task_text")).rstrip() + "\n" + watchdog_block
    return updated


def _write_patch_task(root: Path, task: dict[str, Any]) -> dict[str, str]:
    task_id = _safe_token(task.get("task_id"), default="selfaction-patch")
    json_path = root / TASK_DIR_REL / f"{task_id}.json"
    md_path = root / TASK_MD_REL
    write_self_action_patch_executor_json(json_path, task)
    write_self_action_patch_executor_text(root / TASK_MD_REL, _render_task_markdown(task))
    return {
        "json": str(json_path.relative_to(root)).replace("\\", "/"),
        "markdown": str(md_path.relative_to(root)).replace("\\", "/"),
    }


def _render_task_markdown(task: dict[str, Any]) -> str:
    handoff = task.get("handoff") if isinstance(task.get("handoff"), dict) else {}
    return "\n".join(
        [
            "---",
            "title: Self Action Patch Executor Task",
            "memory_type: self_action_patch_executor_task",
            "time_scope: short_term",
            "subject_ids: [xinyu]",
            "protected: true",
            "source: xinyu_self_action_patch_executor",
            f"updated_at: {_safe_str(task.get('created_at'))}",
            "status: active",
            "tags: [initiative, action, codex, patch, local-control]",
            "---",
            "",
            "# Self Action Patch Executor Task",
            "",
            "## Source Handoff",
            f"- task_id: {_safe_str(task.get('task_id'))}",
            f"- queue_id: {_safe_str(handoff.get('queue_id'))}",
            f"- approval_id: {_safe_str(handoff.get('approval_id'))}",
            f"- goal_id: {_safe_str(handoff.get('goal_id'))}",
            f"- action_kind: {_safe_str(handoff.get('action_kind'))}",
            f"- approval_scope: {_safe_str(handoff.get('approval_scope'))}",
            "",
            "## Boundary",
            f"- allowed_scope: {_safe_str(task.get('allowed_scope'))}",
            "- gateway_or_executor_may_send_messages: false",
            "- stable_memory_write: blocked",
            "",
            "## Codex Task",
            _safe_str(task.get("task_text")),
        ]
    )


def _codex_payload(
    task: dict[str, Any],
    *,
    handoff: dict[str, str],
    timeout_seconds: int,
    checked_at: str,
    background: bool = False,
) -> dict[str, Any]:
    approval_id = _safe_str(handoff.get("approval_id"), "unknown")
    task_text = _safe_str(task.get("task_text"))
    codex_text = "用 Codex 执行这个已批准的自行动作代码补丁任务。\n\n" + task_text
    return {
        "text": codex_text,
        "raw_owner_task": codex_text,
        "source": "self_action_patch_executor",
        "background": bool(background),
        "auto_study": False,
        "visible_window": True,
        "window_title": CODEX_WINDOW_TITLE,
        "network_access": False,
        "timeout_seconds": max(30, min(3600, int(timeout_seconds or 1800))),
        "job_id": "selfaction-patch-" + _timestamp_id(checked_at),
        "metadata": {
            "is_owner_user": True,
            "self_action_patch_executor": True,
            "self_code_iteration": True,
            "owner_local_write_approved": True,
            "approval_id": approval_id,
            "gateway_queue_id": _safe_str(handoff.get("queue_id")),
        },
    }


def _codex_result(result: Any) -> dict[str, Any]:
    accepted = bool(getattr(result, "accepted", False))
    timed_out = bool(getattr(result, "timed_out", False))
    exit_code = getattr(result, "exit_code", None)
    if timed_out:
        status = "timed_out"
    elif accepted:
        status = "finished"
    else:
        status = "failed"
    return {
        "status": status,
        "accepted": accepted,
        "timed_out": timed_out,
        "exit_code": exit_code,
        "reply": _compact(getattr(result, "reply", ""), 300),
        "request_path": _safe_str(getattr(result, "request_path", "")),
        "workspace_path": _safe_str(getattr(result, "workspace_path", "")),
        "report_path": _safe_str(getattr(result, "report_path", "")),
        "last_message_path": _safe_str(getattr(result, "last_message_path", "")),
        "notes": [_safe_str(note) for note in getattr(result, "notes", [])[:8]],
    }


def _status_from_codex(codex: dict[str, Any]) -> str:
    status = _safe_str(codex.get("status"))
    if status == "finished":
        return "codex_completed"
    if status == "timed_out":
        return "codex_timed_out"
    return "codex_failed"


def _persist_result(root: Path, result: dict[str, Any]) -> None:
    previous = _read_json(root / STATE_JSON_REL, default={})
    history = previous.get("history") if isinstance(previous, dict) and isinstance(previous.get("history"), list) else []
    codex = result.get("codex") if isinstance(result.get("codex"), dict) else {}
    state = {
        "version": EXECUTOR_VERSION,
        "updated_at": _timestamp_or_now_iso(result.get("checked_at")),
        "status": _safe_str(result.get("status")),
        "execution_level": _safe_str(result.get("execution_level")),
        "last_queue_id": _safe_str(result.get("queue_id")),
        "last_approval_id": _safe_str(result.get("approval_id")),
        "last_goal_id": _safe_str(result.get("goal_id")),
        "last_action_kind": _safe_str(result.get("action_kind")),
        "last_task_id": _safe_str(result.get("task_id")),
        "last_task_path": _safe_str(result.get("task_path")),
        "last_task_markdown_path": _safe_str(result.get("task_markdown_path")),
        "last_codex_status": _safe_str(codex.get("status"), "none"),
        "last_report_path": _safe_str(codex.get("report_path")),
        "last_error": _safe_str(result.get("reason")),
        "history": [*history, _history_record(result)][-50:],
    }
    write_self_action_patch_executor_json(root / STATE_JSON_REL, state)
    write_self_action_patch_executor_text(root / STATE_MD_REL, _render_state_markdown(state, result))
    append_self_action_patch_executor_trace(
        root / TRACE_REL,
        {"event_kind": "self_action_patch_executor_run", **_history_record(result)},
    )


def _render_state_markdown(state: dict[str, Any], result: dict[str, Any]) -> str:
    notes = result.get("notes") if isinstance(result.get("notes"), list) else []
    note_lines = "\n".join(f"- {_compact(note, 180)}" for note in notes) or "- none"
    return f"""---
title: Self Action Patch Executor State
memory_type: self_action_patch_executor_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_self_action_patch_executor
updated_at: {_timestamp_or_now_iso(state.get('updated_at'))}
status: active
tags: [initiative, action, codex, patch, local-control]
---

# Self Action Patch Executor State

## Last Run
- checked_at: {_timestamp_or_now_iso(state.get('updated_at'))}
- status: {_safe_str(state.get('status'), 'none')}
- execution_level: {_safe_str(state.get('execution_level'), 'none')}
- queue_id: {_safe_str(state.get('last_queue_id'), 'none')}
- approval_id: {_safe_str(state.get('last_approval_id'), 'none')}
- goal_id: {_safe_str(state.get('last_goal_id'), 'none')}
- action_kind: {_safe_str(state.get('last_action_kind'), 'none')}
- task_id: {_safe_str(state.get('last_task_id'), 'none')}
- codex_status: {_safe_str(state.get('last_codex_status'), 'none')}
- report_path: {_compact(state.get('last_report_path'), 500, default='none')}
- task_path: {_compact(state.get('last_task_path'), 500, default='none')}

## Boundary
- prepare_mode: writes a local patch task only
- schedule_codex_mode: requires allow_codex true, creates watchdog snapshot, then queues background Codex
- execute_codex_mode: requires allow_codex true, creates watchdog snapshot before synchronous Codex
- outward_send: blocked
- stable_memory_write: blocked

## Notes
{note_lines}
"""


def _history_record(result: dict[str, Any]) -> dict[str, Any]:
    codex = result.get("codex") if isinstance(result.get("codex"), dict) else {}
    return {
        "checked_at": _safe_str(result.get("checked_at")),
        "status": _safe_str(result.get("status")),
        "execution_level": _safe_str(result.get("execution_level")),
        "queue_id": _safe_str(result.get("queue_id")),
        "approval_id": _safe_str(result.get("approval_id")),
        "goal_id": _safe_str(result.get("goal_id")),
        "action_kind": _safe_str(result.get("action_kind")),
        "task_id": _safe_str(result.get("task_id")),
        "task_path": _safe_str(result.get("task_path")),
        "codex_status": _safe_str(codex.get("status"), "none"),
        "report_path": _safe_str(codex.get("report_path")),
        "reason": _safe_str(result.get("reason")),
    }


def _blocked_result(
    checked_at: str,
    reason: str,
    execution_level: str,
    *,
    handoff: dict[str, Any] | None = None,
) -> dict[str, Any]:
    handoff = handoff if isinstance(handoff, dict) else {}
    return {
        "accepted": False,
        "status": "blocked",
        "reason": reason,
        "checked_at": checked_at,
        "execution_level": execution_level,
        "queue_id": _safe_str(handoff.get("queue_id")),
        "approval_id": _safe_str(handoff.get("approval_id")),
        "goal_id": _safe_str(handoff.get("goal_id")),
        "action_kind": _safe_str(handoff.get("action_kind")),
        "approval_scope": _safe_str(handoff.get("approval_scope")),
        "task_id": "",
        "task_path": "",
        "task_markdown_path": "",
        "codex": {"status": "blocked", "reason": reason},
        "watchdog": {},
        "notes": [f"patch_executor_blocked:{reason}"],
    }


def _markdown_fields(text: str) -> dict[str, str]:
    return {match.group(1): match.group(2).strip() for match in _FIELD_RE.finditer(text or "")}


def _read_json(path: Path, *, default: Any) -> Any:
    return read_self_action_patch_executor_json(path, default=default)


def _read_text(path: Path, *, limit: int) -> str:
    return read_self_action_patch_executor_text(path, limit=limit)


def _hash_json(value: Any, *, length: int) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()[:length]


def _compact(value: Any, limit: int, *, default: str = "") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_token(value: Any, *, default: str = "") -> str:
    text = _safe_str(value).strip().lower()
    text = re.sub(r"[^a-z0-9_.-]+", "-", text).strip(".-")
    return text[:100] or default


def _timestamp_id(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "", _safe_str(value))[:20] or datetime.now().strftime("%Y%m%dT%H%M%S")


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
    parser = argparse.ArgumentParser(description="Run XinYu self action patch executor.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--checked-at", default=None)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--execute-codex", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    execution_level = "execute_codex" if args.execute_codex else "prepare"
    result = run_self_action_patch_executor(
        args.root,
        checked_at=args.checked_at,
        execution_level=execution_level,
        allow_codex=bool(args.execute_codex),
        timeout_seconds=args.timeout_seconds,
        force=bool(args.force),
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status={result.get('status')}")
        print(f"execution_level={result.get('execution_level')}")
        print(f"task_id={result.get('task_id')}")
        print(f"codex_status={result.get('codex', {}).get('status') if isinstance(result.get('codex'), dict) else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
