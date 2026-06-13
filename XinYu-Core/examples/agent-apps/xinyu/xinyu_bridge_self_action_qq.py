from __future__ import annotations

from typing import Any

from xinyu_bridge_values import safe_str
from xinyu_qq_outbox import enqueue_owner_qq_outbox_message
from xinyu_self_action_voice import (
    compose_self_action_approval_voice,
    compose_self_action_prepared_patch_voice,
)


def maybe_enqueue_self_action_approval_to_qq(
    runtime: Any,
    action_gateway: dict[str, Any],
    *,
    checked_at: str,
) -> list[str]:
    queued_items = action_gateway.get("approval_queue_items") if isinstance(action_gateway, dict) else []
    if not isinstance(queued_items, list):
        return []
    notes: list[str] = []
    for item in queued_items[:2]:
        if not isinstance(item, dict) or not item.get("queued"):
            continue
        queue_id = safe_str(item.get("queue_id")).strip()
        if not queue_id:
            continue
        action_kind = safe_str(item.get("action_kind"), "unknown")
        params = item.get("params") if isinstance(item.get("params"), dict) else {}
        queued = enqueue_owner_qq_outbox_message(
            runtime.xinyu_dir,
            message=compose_self_action_approval_voice(item),
            source="self_action_approval_request",
            dedupe_key=f"self_action_approval_request:persona_voice_v1:{queue_id}",
            metadata={
                "source": "self_action_approval_request",
                "control_plane": True,
                "qq_visible_control_plane_allowed": True,
                "self_action_approval_request": True,
                "self_action_queue_id": queue_id,
                "self_action_action_kind": action_kind,
                "self_action_goal_id": safe_str(item.get("goal_id")),
                "self_action_approval_scope": safe_str(params.get("approval_scope")),
                "self_action_authorize_existing": False,
                "checked_at": checked_at,
            },
        )
        notes.append(
            "self_action_qq_push:"
            f"{queue_id}/"
            f"{'queued' if queued.get('queued') else safe_str((queued.get('notes') or ['not_queued'])[0])}"
        )
    return notes


def maybe_enqueue_self_action_prepared_patch_to_qq(
    runtime: Any,
    patch_executor: dict[str, Any],
    *,
    checked_at: str,
) -> list[str]:
    if not isinstance(patch_executor, dict):
        return []
    codex = patch_executor.get("codex") if isinstance(patch_executor.get("codex"), dict) else {}
    if (
        safe_str(patch_executor.get("status")) != "prepared"
        or safe_str(codex.get("status"), "not_requested") != "not_requested"
        or safe_str(patch_executor.get("action_kind")) != "self_code_patch_request"
    ):
        return []
    queue_id = safe_str(patch_executor.get("queue_id")).strip()
    task_id = safe_str(patch_executor.get("task_id")).strip()
    approval_id = safe_str(patch_executor.get("approval_id")).strip()
    if not queue_id or not task_id:
        return []
    queued = enqueue_owner_qq_outbox_message(
        runtime.xinyu_dir,
        message=compose_self_action_prepared_patch_voice(patch_executor),
        source="self_action_prepared_patch_authorization",
        dedupe_key=(
            "self_action_prepared_patch_authorization:"
            f"persona_voice_v1:{approval_id or queue_id}:{task_id}"
        ),
        metadata={
            "source": "self_action_prepared_patch_authorization",
            "control_plane": True,
            "qq_visible_control_plane_allowed": True,
            "self_action_approval_request": True,
            "self_action_queue_id": queue_id,
            "self_action_approval_id": approval_id,
            "self_action_task_id": task_id,
            "self_action_action_kind": "self_code_patch_request",
            "self_action_authorize_existing": True,
            "checked_at": checked_at,
        },
    )
    return [
        "self_action_prepared_qq_push:"
        f"{queue_id}/"
        f"{'queued' if queued.get('queued') else safe_str((queued.get('notes') or ['not_queued'])[0])}"
    ]
