from __future__ import annotations

from typing import Any

from xinyu_bridge_desktop_self_action_approval_payload import DesktopSelfActionApprovalPayload, SafeStrFunc


def should_attach_pending_patch_executor(
    result: dict[str, Any],
    request: DesktopSelfActionApprovalPayload,
    pending_item: dict[str, Any],
    *,
    safe_str_func: SafeStrFunc,
) -> bool:
    return (
        bool(result.get("accepted"))
        and request.decision == "approved"
        and request.execute
        and safe_str_func(pending_item.get("action_kind")) == "self_code_patch_request"
    )


def should_authorize_existing_handoff(
    result: dict[str, Any],
    request: DesktopSelfActionApprovalPayload,
    *,
    safe_str_func: SafeStrFunc,
) -> bool:
    return (
        not result.get("accepted")
        and safe_str_func(result.get("reason")) == "no_pending_approval"
        and request.decision == "approved"
        and request.authorize_codex
        and request.authorize_existing
    )


def should_keep_existing_denied_noop(
    result: dict[str, Any],
    request: DesktopSelfActionApprovalPayload,
    *,
    safe_str_func: SafeStrFunc,
) -> bool:
    return (
        not result.get("accepted")
        and safe_str_func(result.get("reason")) == "no_pending_approval"
        and request.decision == "denied"
        and request.authorize_existing
    )


def existing_handoff_authorized_result(queue_id: str) -> dict[str, Any]:
    return {
        "accepted": True,
        "status": "completed",
        "decision": "approved",
        "queue_id": queue_id,
        "execute_requested": True,
        "codex_execution_authorized": True,
        "notes": ["self_action_existing_handoff_authorized"],
    }


def existing_handoff_denied_result(queue_id: str) -> dict[str, Any]:
    return {
        "accepted": True,
        "status": "kept_prepared_not_executed",
        "decision": "denied",
        "queue_id": queue_id,
        "execute_requested": False,
        "codex_execution_authorized": False,
        "notes": ["self_action_existing_handoff_denied_noop"],
    }


def apply_existing_patch_executor_result(
    result: dict[str, Any],
    queue_id: str,
    *,
    safe_str_func: SafeStrFunc,
) -> None:
    patch_executor = result.get("patch_executor") if isinstance(result.get("patch_executor"), dict) else {}
    result["queue_id"] = safe_str_func(patch_executor.get("queue_id") or queue_id)
    result["approval_id"] = safe_str_func(patch_executor.get("approval_id"))
    result["status"] = safe_str_func(patch_executor.get("status"), "blocked")
    if not patch_executor.get("accepted"):
        result["accepted"] = False
        result["reason"] = safe_str_func(patch_executor.get("reason"), "patch_executor_blocked")
