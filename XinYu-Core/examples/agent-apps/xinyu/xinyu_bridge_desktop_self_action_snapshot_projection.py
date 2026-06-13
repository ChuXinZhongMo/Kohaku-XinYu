from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_desktop_self_action_snapshot_sections import (
    desktop_self_action_approval_queue_section,
    desktop_self_action_gateway_section,
    desktop_self_action_handoff_section,
    desktop_self_action_patch_executor_section,
)


def desktop_public_candidate(
    candidate: Any,
    *,
    safe_str_func: Callable[..., str],
    safe_dict_func: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    data = safe_dict_func(candidate)
    return {
        "actionId": safe_str_func(data.get("action_id")),
        "goalId": safe_str_func(data.get("goal_id")),
        "actionKind": safe_str_func(data.get("action_kind")),
        "label": safe_str_func(data.get("label")),
        "risk": safe_str_func(data.get("risk")),
        "requiresApproval": bool(data.get("requires_approval")),
        "tool": safe_str_func(data.get("tool")),
        "reason": safe_str_func(data.get("reason")),
    }


def desktop_public_approval_event(
    event: Any,
    *,
    safe_str_func: Callable[..., str],
    safe_dict_func: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    data = safe_dict_func(event)
    return {
        "eventKind": safe_str_func(data.get("event_kind")),
        "queueId": safe_str_func(data.get("queue_id")),
        "approvalId": safe_str_func(data.get("approval_id")),
        "goalId": safe_str_func(data.get("goal_id")),
        "actionKind": safe_str_func(data.get("action_kind")),
        "status": safe_str_func(data.get("status")),
        "decision": safe_str_func(data.get("decision")),
        "result": safe_str_func(data.get("result")),
        "queuedAt": safe_str_func(data.get("queued_at")),
        "decidedAt": safe_str_func(data.get("decided_at")),
        "checkedAt": safe_str_func(data.get("checked_at")),
    }


def desktop_self_action_snapshot_projection(
    sources: dict[str, Any],
    labels: dict[str, Any],
    *,
    gateway_state_rel: Path,
    approval_handoff_rel: Path,
    patch_state_rel: Path,
    patch_task_md_rel: Path,
    approval_queue_rel: Path,
    metric_int_func: Callable[[Any], int],
    safe_str_func: Callable[..., str],
    safe_dict_func: Callable[[Any], dict[str, Any]],
    safe_list_func: Callable[[Any], list[Any]],
    public_candidate_func: Callable[..., dict[str, Any]],
    public_approval_event_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    gateway_state = safe_dict_func(sources.get("gateway_state"))
    patch_state = safe_dict_func(sources.get("patch_state"))
    last_run = safe_dict_func(sources.get("last_run"))
    approval_queue = safe_dict_func(sources.get("approval_queue"))
    latest_execution = safe_dict_func(sources.get("latest_execution"))
    handoff_fields = safe_dict_func(sources.get("handoff_fields"))
    task_fields = safe_dict_func(sources.get("task_fields"))

    pending_count = metric_int_func(labels.get("pending_count"))
    selected_goal_id = safe_str_func(labels.get("selected_goal_id"))
    selected_action_kind = safe_str_func(labels.get("selected_action_kind"))
    patch_status = safe_str_func(labels.get("patch_status"))
    codex_status = safe_str_func(labels.get("codex_status"))
    candidate_actions = [
        public_candidate_func(candidate, safe_str_func=safe_str_func)
        for candidate in safe_list_func(gateway_state.get("last_candidates"))[:4]
    ]

    return {
        "observed": bool(labels.get("observed")),
        "updatedAt": safe_str_func(gateway_state.get("updated_at") or patch_state.get("updated_at")),
        "selectedGoalId": selected_goal_id,
        "selectedActionKind": selected_action_kind,
        "pendingApprovalCount": pending_count,
        "latestPendingQueueId": safe_str_func(approval_queue.get("latest_pending_queue_id")),
        "latestApprovalEvent": public_approval_event_func(sources.get("latest_event"), safe_str_func=safe_str_func),
        "approvalQueue": desktop_self_action_approval_queue_section(
            approval_queue,
            pending_count=pending_count,
            metric_int_func=metric_int_func,
            safe_str_func=safe_str_func,
        ),
        "gateway": desktop_self_action_gateway_section(
            last_run,
            selected_goal_id=selected_goal_id,
            pending_count=pending_count,
            metric_int_func=metric_int_func,
            safe_str_func=safe_str_func,
        ),
        "handoff": desktop_self_action_handoff_section(
            handoff_fields,
            latest_execution,
            approval_handoff_rel=approval_handoff_rel,
            safe_str_func=safe_str_func,
        ),
        "patchExecutor": desktop_self_action_patch_executor_section(
            patch_state,
            task_fields,
            patch_task_md_rel=patch_task_md_rel,
            patch_status=patch_status,
            codex_status=codex_status,
            safe_str_func=safe_str_func,
        ),
        "candidateActions": candidate_actions,
        "paths": {
            "gatewayState": gateway_state_rel.as_posix(),
            "approvalQueue": approval_queue_rel.as_posix(),
            "handoff": approval_handoff_rel.as_posix(),
            "patchState": patch_state_rel.as_posix(),
            "patchTask": patch_task_md_rel.as_posix(),
        },
        "notes": safe_list_func(labels.get("notes")),
    }
