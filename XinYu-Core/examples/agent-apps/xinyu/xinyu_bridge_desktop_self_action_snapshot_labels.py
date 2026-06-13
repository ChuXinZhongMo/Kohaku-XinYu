from __future__ import annotations

from typing import Any, Callable


def desktop_self_action_snapshot_labels(
    sources: dict[str, Any],
    *,
    metric_int_func: Callable[[Any], int],
    safe_str_func: Callable[..., str],
    safe_dict_func: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    gateway_state = safe_dict_func(sources.get("gateway_state"))
    patch_state = safe_dict_func(sources.get("patch_state"))
    approval_queue = safe_dict_func(sources.get("approval_queue"))
    latest_execution = safe_dict_func(sources.get("latest_execution"))
    last_run = safe_dict_func(sources.get("last_run"))
    handoff_fields = safe_dict_func(sources.get("handoff_fields"))
    task_fields = safe_dict_func(sources.get("task_fields"))
    latest_event = safe_dict_func(sources.get("latest_event"))
    latest_patch_history = safe_dict_func(sources.get("latest_patch_history"))
    approval_queue_events = sources.get("approval_queue_events")

    pending_count = metric_int_func(approval_queue.get("pending_count", gateway_state.get("pending_approval_count")))
    selected_goal_id = safe_str_func(
        last_run.get("selected_goal_id")
        or latest_execution.get("goal_id")
        or patch_state.get("last_goal_id")
        or handoff_fields.get("goal_id")
    )
    selected_action_kind = safe_str_func(
        latest_execution.get("action_kind")
        or patch_state.get("last_action_kind")
        or handoff_fields.get("action_kind")
        or latest_event.get("action_kind")
    )
    patch_status = safe_str_func(patch_state.get("status") or latest_patch_history.get("status"))
    codex_status = safe_str_func(patch_state.get("last_codex_status") or latest_patch_history.get("codex_status"))
    observed = bool(gateway_state or patch_state or approval_queue_events or handoff_fields or task_fields)
    notes = desktop_self_action_snapshot_notes(
        observed=observed,
        patch_status=patch_status,
        codex_status=codex_status,
    )

    return {
        "observed": observed,
        "pending_count": pending_count,
        "selected_goal_id": selected_goal_id,
        "selected_action_kind": selected_action_kind,
        "patch_status": patch_status,
        "codex_status": codex_status,
        "notes": notes,
    }


def desktop_self_action_snapshot_notes(*, observed: bool, patch_status: str, codex_status: str) -> list[str]:
    notes: list[str] = []
    if not observed:
        notes.append("self_action_state_not_observed")
    if patch_status == "prepared" and codex_status == "not_requested":
        notes.append("codex_execution_not_requested")
    return notes
