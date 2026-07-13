from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_values import safe_str


def append_goal_ecology_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_self_chosen_goal_ecology_func: Callable[..., dict[str, Any]],
) -> None:
    try:
        goal_ecology = run_self_chosen_goal_ecology_func(
            runtime.xinyu_dir,
            checked_at=checked_at,
            trigger="autonomous_maintenance",
        )
        notes.append(
            "goal_ecology:"
            f"{safe_str(goal_ecology.get('selected_goal_id'), 'unknown')}/"
            f"{safe_str(goal_ecology.get('selected_score'), '0')}"
        )
    except Exception as exc:
        notes.append(f"goal_ecology_error:{type(exc).__name__}")
        runtime._trace_autonomous(f"goal_ecology_error={exc!r}")


def append_self_action_gateway_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_self_action_gateway_func: Callable[..., dict[str, Any]],
) -> None:
    try:
        action_gateway = run_self_action_gateway_func(
            runtime.xinyu_dir,
            checked_at=checked_at,
            trigger="autonomous_maintenance",
        )
        notes.append(
            "self_action_gateway:"
            f"{safe_str(action_gateway.get('status'), 'unknown')}/"
            f"{safe_str(action_gateway.get('selected_goal_id'), 'none')}/"
            f"{safe_str(action_gateway.get('executed_action_count'), '0')}/"
            f"{safe_str(action_gateway.get('queued_approval_count'), '0')}"
        )
        notes.extend(safe_str(note) for note in action_gateway.get("notes", [])[:3])
        notes.extend(runtime._maybe_enqueue_self_action_approval_to_qq(action_gateway, checked_at=checked_at))
    except Exception as exc:
        notes.append(f"self_action_gateway_error:{type(exc).__name__}")
        runtime._trace_autonomous(f"self_action_gateway_error={exc!r}")


def append_action_followup_audit_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_audit_and_queue_followups_func: Callable[..., dict[str, Any]],
) -> None:
    try:
        result = run_audit_and_queue_followups_func(runtime.xinyu_dir)
        queued = int((result.get("followup_queue") or {}).get("queued_count") or 0)
        pending = int((result.get("followup_queue") or {}).get("pending_count") or 0)
        health = safe_str(result.get("health_status"), "unknown")
        repl = result.get("replicator_pressure") if isinstance(result.get("replicator_pressure"), dict) else {}
        repl_level = safe_str(repl.get("level"), "quiet")
        repl_followup = int(result.get("replicator_followup_count") or 0)
        note = f"action_followup_audit:{health}/queued={queued}/pending={pending}/replicator={repl_level}"
        if repl_level == "alert" and repl_followup > 0:
            note += f"/repl_followup={repl_followup}"
        notes.append(note)
    except Exception as exc:
        notes.append(f"action_followup_audit_error:{type(exc).__name__}")
        runtime._trace_autonomous(f"action_followup_audit_error={exc!r}")


def append_self_action_patch_executor_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_self_action_patch_executor_func: Callable[..., dict[str, Any]],
) -> None:
    try:
        patch_executor = run_self_action_patch_executor_func(
            runtime.xinyu_dir,
            checked_at=checked_at,
            execution_level="prepare",
            allow_codex=False,
        )
        codex = patch_executor.get("codex")
        codex_status = codex.get("status") if isinstance(codex, dict) else "none"
        notes.append(
            "self_action_patch_executor:"
            f"{safe_str(patch_executor.get('status'), 'unknown')}/"
            f"{safe_str(patch_executor.get('task_id'), 'none')}/"
            f"{safe_str(codex_status, 'none')}"
        )
        notes.extend(safe_str(note) for note in patch_executor.get("notes", [])[:2])
        notes.extend(runtime._maybe_enqueue_self_action_prepared_patch_to_qq(patch_executor, checked_at=checked_at))
    except Exception as exc:
        notes.append(f"self_action_patch_executor_error:{type(exc).__name__}")
        runtime._trace_autonomous(f"self_action_patch_executor_error={exc!r}")
