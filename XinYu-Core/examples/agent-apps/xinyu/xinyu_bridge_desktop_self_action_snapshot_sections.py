from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def desktop_self_action_approval_queue_section(
    approval_queue: dict[str, Any],
    *,
    pending_count: int,
    metric_int_func: Callable[[Any], int],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    return {
        "pendingCount": pending_count,
        "approvedWaitingExecutionCount": metric_int_func(approval_queue.get("approved_waiting_execution_count")),
        "executedCount": metric_int_func(approval_queue.get("executed_count")),
        "deniedCount": metric_int_func(approval_queue.get("denied_count")),
        "blockedExecutionCount": metric_int_func(approval_queue.get("blocked_execution_count")),
        "latestPendingQueueId": safe_str_func(approval_queue.get("latest_pending_queue_id")),
        "latestApprovedQueueId": safe_str_func(approval_queue.get("latest_approved_queue_id")),
        "latestExecutedQueueId": safe_str_func(approval_queue.get("latest_executed_queue_id")),
    }


def desktop_self_action_gateway_section(
    last_run: dict[str, Any],
    *,
    selected_goal_id: str,
    pending_count: int,
    metric_int_func: Callable[[Any], int],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    return {
        "checkedAt": safe_str_func(last_run.get("checked_at")),
        "selectedGoalId": selected_goal_id,
        "candidateCount": metric_int_func(last_run.get("candidate_count")),
        "executedActionCount": metric_int_func(last_run.get("executed_action_count")),
        "queuedApprovalCount": metric_int_func(last_run.get("queued_approval_count")),
        "pendingApprovalCount": pending_count,
    }


def desktop_self_action_handoff_section(
    handoff_fields: dict[str, Any],
    latest_execution: dict[str, Any],
    *,
    approval_handoff_rel: Path,
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    return {
        "exists": bool(handoff_fields),
        "path": approval_handoff_rel.as_posix(),
        "queueId": safe_str_func(handoff_fields.get("queue_id") or latest_execution.get("queue_id")),
        "approvalId": safe_str_func(handoff_fields.get("approval_id") or latest_execution.get("approval_id")),
        "goalId": safe_str_func(handoff_fields.get("goal_id") or latest_execution.get("goal_id")),
        "actionKind": safe_str_func(handoff_fields.get("action_kind") or latest_execution.get("action_kind")),
        "approvalScope": safe_str_func(
            handoff_fields.get("approval_scope") or latest_execution.get("approval_scope")
        ),
        "executionMode": safe_str_func(handoff_fields.get("execution_mode")),
        "nextExecutor": safe_str_func(handoff_fields.get("next_executor")),
        "executionResult": safe_str_func(latest_execution.get("execution_result")),
    }


def desktop_self_action_patch_executor_section(
    patch_state: dict[str, Any],
    task_fields: dict[str, Any],
    *,
    patch_task_md_rel: Path,
    patch_status: str,
    codex_status: str,
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    return {
        "updatedAt": safe_str_func(patch_state.get("updated_at")),
        "status": patch_status,
        "executionLevel": safe_str_func(patch_state.get("execution_level")),
        "queueId": safe_str_func(patch_state.get("last_queue_id") or task_fields.get("queue_id")),
        "approvalId": safe_str_func(patch_state.get("last_approval_id") or task_fields.get("approval_id")),
        "goalId": safe_str_func(patch_state.get("last_goal_id") or task_fields.get("goal_id")),
        "actionKind": safe_str_func(patch_state.get("last_action_kind") or task_fields.get("action_kind")),
        "taskId": safe_str_func(patch_state.get("last_task_id") or task_fields.get("task_id")),
        "taskPath": safe_str_func(patch_state.get("last_task_path")),
        "taskMarkdownPath": safe_str_func(
            patch_state.get("last_task_markdown_path") or patch_task_md_rel.as_posix()
        ),
        "codexStatus": codex_status,
        "reportPath": safe_str_func(patch_state.get("last_report_path")),
        "lastError": safe_str_func(patch_state.get("last_error")),
    }
