from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_action_experience_digest import read_recent_action_digest_snapshot
from xinyu_environment_sensor import sample_environment
from xinyu_life_kernel import build_entropy_state
from xinyu_bridge_values import safe_str
from stores.self_action_queue import APPROVAL_QUEUE_REL as SELF_ACTION_APPROVAL_QUEUE_REL
from stores.self_action_queue import read_approval_queue_events


SELF_ACTION_GATEWAY_STATE_REL = Path("runtime/self_action_gateway/state.json")
SELF_ACTION_APPROVAL_HANDOFF_REL = Path("memory/context/self_action_gateway_execution_handoff.md")
SELF_ACTION_PATCH_STATE_REL = Path("runtime/self_action_patch_executor/state.json")
SELF_ACTION_PATCH_TASK_MD_REL = Path("memory/context/self_action_patch_executor_task.md")


def desktop_metric_int(value: Any) -> int:
    try:
        return max(0, int(safe_str(value).strip()))
    except (TypeError, ValueError):
        return 0


def desktop_initiative_metrics_summary(metrics: dict[str, Any]) -> dict[str, Any]:
    if not metrics or safe_str(metrics.get("observed")) == "false":
        return {"observed": False}
    return {
        "observed": True,
        "updatedAt": safe_str(metrics.get("updated_at")),
        "windowHours": desktop_metric_int(metrics.get("window_hours")),
        "eventCount24h": desktop_metric_int(metrics.get("event_count_24h")),
        "desktopShown24h": desktop_metric_int(metrics.get("desktop_shown_count_24h")),
        "heldPrivate24h": desktop_metric_int(metrics.get("held_private_count_24h")),
        "blocked24h": desktop_metric_int(metrics.get("blocked_count_24h")),
        "feedbackCount24h": desktop_metric_int(metrics.get("feedback_count_24h")),
        "dismissCount24h": desktop_metric_int(metrics.get("dismiss_count_24h")),
        "replyCount24h": desktop_metric_int(metrics.get("reply_count_24h")),
        "approvedQqCount24h": desktop_metric_int(metrics.get("approved_qq_count_24h")),
        "failedCount24h": desktop_metric_int(metrics.get("failed_count_24h")),
        "pendingFeedbackCount": desktop_metric_int(metrics.get("pending_feedback_count")),
    }


def _desktop_safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _desktop_safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _desktop_read_json_dict(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return _desktop_safe_dict(data)


def _desktop_read_markdown_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return fields
    for line in lines:
        clean = line.strip()
        if not clean.startswith("- ") or ":" not in clean:
            continue
        key, value = clean[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _desktop_public_candidate(candidate: Any) -> dict[str, Any]:
    data = _desktop_safe_dict(candidate)
    return {
        "actionId": safe_str(data.get("action_id")),
        "goalId": safe_str(data.get("goal_id")),
        "actionKind": safe_str(data.get("action_kind")),
        "label": safe_str(data.get("label")),
        "risk": safe_str(data.get("risk")),
        "requiresApproval": bool(data.get("requires_approval")),
        "tool": safe_str(data.get("tool")),
        "reason": safe_str(data.get("reason")),
    }


def _desktop_public_approval_event(event: Any) -> dict[str, Any]:
    data = _desktop_safe_dict(event)
    return {
        "eventKind": safe_str(data.get("event_kind")),
        "queueId": safe_str(data.get("queue_id")),
        "approvalId": safe_str(data.get("approval_id")),
        "goalId": safe_str(data.get("goal_id")),
        "actionKind": safe_str(data.get("action_kind")),
        "status": safe_str(data.get("status")),
        "decision": safe_str(data.get("decision")),
        "result": safe_str(data.get("result")),
        "queuedAt": safe_str(data.get("queued_at")),
        "decidedAt": safe_str(data.get("decided_at")),
        "checkedAt": safe_str(data.get("checked_at")),
    }


def desktop_self_action_snapshot(root: Path) -> dict[str, Any]:
    gateway_state = _desktop_read_json_dict(root / SELF_ACTION_GATEWAY_STATE_REL)
    patch_state = _desktop_read_json_dict(root / SELF_ACTION_PATCH_STATE_REL)
    approval_queue_events = read_approval_queue_events(root, limit=12)
    handoff_fields = _desktop_read_markdown_fields(root / SELF_ACTION_APPROVAL_HANDOFF_REL)
    task_fields = _desktop_read_markdown_fields(root / SELF_ACTION_PATCH_TASK_MD_REL)

    last_run = _desktop_safe_dict(gateway_state.get("last_run"))
    approval_queue = _desktop_safe_dict(gateway_state.get("approval_queue"))
    latest_execution = _desktop_safe_dict(gateway_state.get("latest_approval_execution"))
    latest_event = approval_queue_events[-1] if approval_queue_events else {}
    candidate_actions = [_desktop_public_candidate(candidate) for candidate in _desktop_safe_list(gateway_state.get("last_candidates"))[:4]]

    pending_count = desktop_metric_int(approval_queue.get("pending_count", gateway_state.get("pending_approval_count")))
    selected_goal_id = safe_str(
        last_run.get("selected_goal_id")
        or latest_execution.get("goal_id")
        or patch_state.get("last_goal_id")
        or handoff_fields.get("goal_id")
    )
    selected_action_kind = safe_str(
        latest_execution.get("action_kind")
        or patch_state.get("last_action_kind")
        or handoff_fields.get("action_kind")
        or _desktop_safe_dict(latest_event).get("action_kind")
    )
    patch_history = _desktop_safe_list(patch_state.get("history"))
    latest_patch_history = _desktop_safe_dict(patch_history[-1]) if patch_history else {}
    patch_status = safe_str(patch_state.get("status") or latest_patch_history.get("status"))
    codex_status = safe_str(patch_state.get("last_codex_status") or latest_patch_history.get("codex_status"))
    observed = bool(gateway_state or patch_state or approval_queue_events or handoff_fields or task_fields)
    notes: list[str] = []
    if not observed:
        notes.append("self_action_state_not_observed")
    if patch_status == "prepared" and codex_status == "not_requested":
        notes.append("codex_execution_not_requested")

    return {
        "observed": observed,
        "updatedAt": safe_str(gateway_state.get("updated_at") or patch_state.get("updated_at")),
        "selectedGoalId": selected_goal_id,
        "selectedActionKind": selected_action_kind,
        "pendingApprovalCount": pending_count,
        "latestPendingQueueId": safe_str(approval_queue.get("latest_pending_queue_id")),
        "latestApprovalEvent": _desktop_public_approval_event(latest_event),
        "approvalQueue": {
            "pendingCount": pending_count,
            "approvedWaitingExecutionCount": desktop_metric_int(approval_queue.get("approved_waiting_execution_count")),
            "executedCount": desktop_metric_int(approval_queue.get("executed_count")),
            "deniedCount": desktop_metric_int(approval_queue.get("denied_count")),
            "blockedExecutionCount": desktop_metric_int(approval_queue.get("blocked_execution_count")),
            "latestPendingQueueId": safe_str(approval_queue.get("latest_pending_queue_id")),
            "latestApprovedQueueId": safe_str(approval_queue.get("latest_approved_queue_id")),
            "latestExecutedQueueId": safe_str(approval_queue.get("latest_executed_queue_id")),
        },
        "gateway": {
            "checkedAt": safe_str(last_run.get("checked_at")),
            "selectedGoalId": selected_goal_id,
            "candidateCount": desktop_metric_int(last_run.get("candidate_count")),
            "executedActionCount": desktop_metric_int(last_run.get("executed_action_count")),
            "queuedApprovalCount": desktop_metric_int(last_run.get("queued_approval_count")),
            "pendingApprovalCount": pending_count,
        },
        "handoff": {
            "exists": bool(handoff_fields),
            "path": SELF_ACTION_APPROVAL_HANDOFF_REL.as_posix(),
            "queueId": safe_str(handoff_fields.get("queue_id") or latest_execution.get("queue_id")),
            "approvalId": safe_str(handoff_fields.get("approval_id") or latest_execution.get("approval_id")),
            "goalId": safe_str(handoff_fields.get("goal_id") or latest_execution.get("goal_id")),
            "actionKind": safe_str(handoff_fields.get("action_kind") or latest_execution.get("action_kind")),
            "approvalScope": safe_str(handoff_fields.get("approval_scope") or latest_execution.get("approval_scope")),
            "executionMode": safe_str(handoff_fields.get("execution_mode")),
            "nextExecutor": safe_str(handoff_fields.get("next_executor")),
            "executionResult": safe_str(latest_execution.get("execution_result")),
        },
        "patchExecutor": {
            "updatedAt": safe_str(patch_state.get("updated_at")),
            "status": patch_status,
            "executionLevel": safe_str(patch_state.get("execution_level")),
            "queueId": safe_str(patch_state.get("last_queue_id") or task_fields.get("queue_id")),
            "approvalId": safe_str(patch_state.get("last_approval_id") or task_fields.get("approval_id")),
            "goalId": safe_str(patch_state.get("last_goal_id") or task_fields.get("goal_id")),
            "actionKind": safe_str(patch_state.get("last_action_kind") or task_fields.get("action_kind")),
            "taskId": safe_str(patch_state.get("last_task_id") or task_fields.get("task_id")),
            "taskPath": safe_str(patch_state.get("last_task_path")),
            "taskMarkdownPath": safe_str(patch_state.get("last_task_markdown_path") or SELF_ACTION_PATCH_TASK_MD_REL.as_posix()),
            "codexStatus": codex_status,
            "reportPath": safe_str(patch_state.get("last_report_path")),
            "lastError": safe_str(patch_state.get("last_error")),
        },
        "candidateActions": candidate_actions,
        "paths": {
            "gatewayState": SELF_ACTION_GATEWAY_STATE_REL.as_posix(),
            "approvalQueue": SELF_ACTION_APPROVAL_QUEUE_REL.as_posix(),
            "handoff": SELF_ACTION_APPROVAL_HANDOFF_REL.as_posix(),
            "patchState": SELF_ACTION_PATCH_STATE_REL.as_posix(),
            "patchTask": SELF_ACTION_PATCH_TASK_MD_REL.as_posix(),
        },
        "notes": notes,
    }


async def desktop_snapshot(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    await runtime._ensure_self_choice_ready()
    await runtime.self_choice_store.apply_time_decay()
    self_choice_private = await runtime.self_choice_store.snapshot_private()
    event_state = await runtime._desktop_event_state()
    proactive_inbox = await runtime.desktop_proactive_inbox(payload)
    proactive_items = proactive_inbox.get("items", [])
    proactive_history = proactive_inbox.get("history", [])
    recent_turns = (await runtime.desktop_chat_recent(payload)).get("items", [])
    recent_memory_events = (await runtime.desktop_memory_recent(payload)).get("items", [])
    environment = sample_environment(runtime.xinyu_dir)
    entropy = build_entropy_state(
        environment=environment,
        proactive_items=proactive_items,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
    )
    entropy_state = entropy.model_dump(mode="json")
    active_desires = await runtime._desktop_active_desires(
        environment=environment,
        entropy_state=entropy,
        proactive_items=proactive_items,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
        self_choice_state=self_choice_private,
    )
    self_choice_public = await runtime.self_choice_store.snapshot_public()
    action_digest = read_recent_action_digest_snapshot(runtime.xinyu_dir, limit=5)
    health = runtime.health_snapshot()
    initiative_metrics = (
        health.get("runtime_presence", {}).get("initiative_metrics", {})
        if isinstance(health.get("runtime_presence"), dict)
        else {}
    )
    return {
        "version": 1,
        "snapshotAt": datetime.now().astimezone().isoformat(),
        "lastEventId": event_state.get("latest_event_id", ""),
        "services": runtime._desktop_services(),
        "health": health,
        "environment": environment,
        "entropyState": entropy_state,
        "selfChoiceState": self_choice_public,
        "activeDesires": active_desires,
        "xinyuState": runtime._desktop_xinyu_state(
            environment=environment,
            entropy_state=entropy_state,
            active_desires=active_desires,
            proactive_items=proactive_items,
            recent_turns=recent_turns,
            recent_memory_events=recent_memory_events,
            action_digest=action_digest,
            initiative_metrics=initiative_metrics,
        ),
        "eventBus": event_state,
        "proactiveInbox": proactive_items,
        "proactiveHistory": proactive_history,
        "recentTurns": recent_turns,
        "recentMemoryEvents": recent_memory_events,
        "actionDigestState": action_digest,
        "selfAction": desktop_self_action_snapshot(runtime.xinyu_dir),
        "notes": ["desktop_snapshot_v1_life_state"],
    }
