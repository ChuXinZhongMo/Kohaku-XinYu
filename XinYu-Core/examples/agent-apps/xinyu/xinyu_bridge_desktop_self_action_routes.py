from __future__ import annotations

import asyncio
from datetime import datetime
from http import HTTPStatus
from typing import Any

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_self_action_gateway import decide_self_action_approval, list_self_action_approvals
from xinyu_self_action_patch_executor import run_self_action_patch_executor
from xinyu_self_action_voice import compose_self_action_decision_reply


async def desktop_self_action_approval(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if runtime._closed:
        raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
    if payload is not None and not isinstance(payload, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    payload = payload or {}
    queue_id = _safe_str(payload.get("queueId") or payload.get("queue_id") or "latest").strip() or "latest"
    decision = _safe_str(payload.get("decision")).strip().lower()
    if decision in {"approve", "ok", "accept"}:
        decision = "approved"
    if decision in {"deny", "reject", "rejected"}:
        decision = "denied"
    if decision not in {"approved", "denied"}:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "invalid self action approval decision")
    reason = _safe_str(payload.get("reason") or payload.get("note")).strip()
    execute = _as_bool(payload.get("execute"), default=decision == "approved")
    decided_by = _safe_str(payload.get("decidedBy") or payload.get("decided_by") or "owner_desktop").strip() or "owner_desktop"
    authorization_value = next(
        (
            payload[key]
            for key in (
                "authorizeCodex",
                "authorize_codex",
                "authorizeExecution",
                "authorize_execution",
                "allowCodex",
                "allow_codex",
            )
            if key in payload
        ),
        None,
    )
    authorize_codex = decision == "approved" and execute and _as_bool(authorization_value, default=False)
    authorize_existing_value = next(
        (
            payload[key]
            for key in (
                "authorizeExisting",
                "authorize_existing",
                "authorizePrepared",
                "authorize_prepared",
            )
            if key in payload
        ),
        None,
    )
    authorize_existing = decision == "approved" and execute and _as_bool(authorize_existing_value, default=False)
    timeout_seconds = _safe_str(payload.get("timeoutSeconds") or payload.get("timeout_seconds") or "1800").strip()
    try:
        timeout_seconds_int = max(30, min(3600, int(timeout_seconds)))
    except ValueError:
        timeout_seconds_int = 1800
    checked_at = datetime.now().astimezone().isoformat()
    pending_item = desktop_self_action_pending_item(runtime, queue_id)

    result = await asyncio.to_thread(
        decide_self_action_approval,
        runtime.xinyu_dir,
        queue_id=queue_id,
        decision=decision,
        decided_at=checked_at,
        decided_by=decided_by,
        reason=reason,
        execute=execute,
    )
    result["codex_execution_authorized"] = authorize_codex
    if (
        result.get("accepted")
        and decision == "approved"
        and execute
        and _safe_str(pending_item.get("action_kind")) == "self_code_patch_request"
    ):
        await desktop_attach_self_action_patch_executor(
            runtime,
            result,
            checked_at=checked_at,
            authorize_codex=authorize_codex,
            timeout_seconds=timeout_seconds_int,
        )
    elif (
        not result.get("accepted")
        and _safe_str(result.get("reason")) == "no_pending_approval"
        and decision == "approved"
        and authorize_codex
        and authorize_existing
    ):
        existing_result: dict[str, Any] = {
            "accepted": True,
            "status": "completed",
            "decision": "approved",
            "queue_id": queue_id,
            "execute_requested": True,
            "codex_execution_authorized": True,
            "notes": ["self_action_existing_handoff_authorized"],
        }
        await desktop_attach_self_action_patch_executor(
            runtime,
            existing_result,
            checked_at=checked_at,
            authorize_codex=True,
            timeout_seconds=timeout_seconds_int,
        )
        patch_executor = existing_result.get("patch_executor") if isinstance(existing_result.get("patch_executor"), dict) else {}
        existing_result["queue_id"] = _safe_str(patch_executor.get("queue_id") or queue_id)
        existing_result["approval_id"] = _safe_str(patch_executor.get("approval_id"))
        existing_result["status"] = _safe_str(patch_executor.get("status"), "blocked")
        if not patch_executor.get("accepted"):
            existing_result["accepted"] = False
            existing_result["reason"] = _safe_str(patch_executor.get("reason"), "patch_executor_blocked")
        result = existing_result
    elif (
        not result.get("accepted")
        and _safe_str(result.get("reason")) == "no_pending_approval"
        and decision == "denied"
        and authorize_existing
    ):
        result = {
            "accepted": True,
            "status": "kept_prepared_not_executed",
            "decision": "denied",
            "queue_id": queue_id,
            "execute_requested": False,
            "codex_execution_authorized": False,
            "notes": ["self_action_existing_handoff_denied_noop"],
        }
    snapshot = await runtime.desktop_snapshot({})
    result["selfAction"] = snapshot.get("selfAction")
    result["reply"] = desktop_self_action_approval_reply(result, decision=decision)
    return result


async def desktop_attach_self_action_patch_executor(
    runtime: Any,
    result: dict[str, Any],
    *,
    checked_at: str,
    authorize_codex: bool,
    timeout_seconds: int,
) -> None:
    execution_level = "schedule_codex" if authorize_codex else "prepare"
    patch_executor = await asyncio.to_thread(
        run_self_action_patch_executor,
        runtime.xinyu_dir,
        checked_at=checked_at,
        execution_level=execution_level,
        allow_codex=authorize_codex,
        timeout_seconds=timeout_seconds,
    )
    codex_payload = patch_executor.pop("codex_payload", None)
    result["patch_executor"] = patch_executor
    if authorize_codex and isinstance(codex_payload, dict) and patch_executor.get("accepted"):
        try:
            result["codex_execution"] = await runtime.codex_execute(codex_payload)
        except Exception as exc:
            result["codex_execution"] = {
                "accepted": False,
                "error": type(exc).__name__,
                "message": _safe_str(exc),
                "notes": ["self_action_codex_schedule_failed"],
            }


def desktop_self_action_pending_item(runtime: Any, queue_id: str) -> dict[str, Any]:
    listed = list_self_action_approvals(runtime.xinyu_dir)
    items = listed.get("items") if isinstance(listed.get("items"), list) else []
    pending = [item for item in items if isinstance(item, dict) and _safe_str(item.get("status")) == "pending_owner_approval"]
    resolved_queue_id = queue_id
    if queue_id in {"", "latest", "next"}:
        queue = listed.get("approval_queue") if isinstance(listed.get("approval_queue"), dict) else {}
        resolved_queue_id = _safe_str(queue.get("latest_pending_queue_id"))
    for item in pending:
        if _safe_str(item.get("queue_id")) == resolved_queue_id:
            return item
    return pending[-1] if pending else {}


def desktop_self_action_approval_reply(result: dict[str, Any], *, decision: str) -> str:
    return compose_self_action_decision_reply(result, decision=decision)
