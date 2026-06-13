from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from xinyu_bridge_desktop_self_action_approval_payload import DesktopSelfActionApprovalPayload, SafeStrFunc
from xinyu_bridge_desktop_self_action_approval_response import attach_desktop_self_action_response
from xinyu_bridge_desktop_self_action_approval_routing import (
    apply_existing_patch_executor_result,
    existing_handoff_authorized_result,
    existing_handoff_denied_result,
    should_attach_pending_patch_executor,
    should_authorize_existing_handoff,
    should_keep_existing_denied_noop,
)


ToThreadFunc = Callable[..., Awaitable[Any]]


async def decide_desktop_self_action_approval(
    root: Any,
    request: DesktopSelfActionApprovalPayload,
    *,
    checked_at: str,
    decide_approval_func: Callable[..., dict[str, Any]],
    to_thread_func: ToThreadFunc,
) -> dict[str, Any]:
    result = await to_thread_func(
        decide_approval_func,
        root,
        queue_id=request.queue_id,
        decision=request.decision,
        decided_at=checked_at,
        decided_by=request.decided_by,
        reason=request.reason,
        execute=request.execute,
    )
    result["codex_execution_authorized"] = request.authorize_codex
    return result


async def dispatch_desktop_self_action_approval_result(
    result: dict[str, Any],
    request: DesktopSelfActionApprovalPayload,
    pending_item: dict[str, Any],
    *,
    checked_at: str,
    attach_patch_executor_func: Callable[..., Awaitable[None]],
    snapshot_func: Callable[..., Awaitable[dict[str, Any]]],
    approval_reply_func: Callable[..., str],
    safe_str_func: SafeStrFunc,
) -> dict[str, Any]:
    if should_attach_pending_patch_executor(result, request, pending_item, safe_str_func=safe_str_func):
        await attach_patch_executor_func(
            result,
            checked_at=checked_at,
            authorize_codex=request.authorize_codex,
            timeout_seconds=request.timeout_seconds,
        )
    elif should_authorize_existing_handoff(result, request, safe_str_func=safe_str_func):
        result = existing_handoff_authorized_result(request.queue_id)
        await attach_patch_executor_func(
            result,
            checked_at=checked_at,
            authorize_codex=True,
            timeout_seconds=request.timeout_seconds,
        )
        apply_existing_patch_executor_result(result, request.queue_id, safe_str_func=safe_str_func)
    elif should_keep_existing_denied_noop(result, request, safe_str_func=safe_str_func):
        result = existing_handoff_denied_result(request.queue_id)
    return await attach_desktop_self_action_response(
        result,
        decision=request.decision,
        snapshot_func=snapshot_func,
        approval_reply_func=approval_reply_func,
    )


async def attach_desktop_self_action_patch_executor(
    runtime: Any,
    result: dict[str, Any],
    *,
    checked_at: str,
    authorize_codex: bool,
    timeout_seconds: int,
    run_patch_executor_func: Callable[..., dict[str, Any]],
    to_thread_func: ToThreadFunc,
    safe_str_func: SafeStrFunc,
) -> None:
    execution_level = "schedule_codex" if authorize_codex else "prepare"
    patch_executor = await to_thread_func(
        run_patch_executor_func,
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
                "message": safe_str_func(exc),
                "notes": ["self_action_codex_schedule_failed"],
            }
