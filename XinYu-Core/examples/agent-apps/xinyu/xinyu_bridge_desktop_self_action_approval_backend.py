from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Protocol

import xinyu_bridge_desktop_self_action_approval as self_action_approval
from xinyu_bridge_desktop_self_action_approval_payload import DesktopSelfActionApprovalPayload
from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_SURFACE_FALLBACK_ADAPTER,
    DESKTOP_SURFACE_ROLLBACK,
    DESKTOP_SURFACE_STATE_OWNER,
)
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_self_action_gateway import decide_self_action_approval, list_self_action_approvals
from xinyu_self_action_patch_executor import run_self_action_patch_executor
from xinyu_self_action_voice import compose_self_action_decision_reply


DESKTOP_SURFACE_SELF_ACTION_APPROVAL_BACKEND_RUNTIME_ATTR = "_desktop_surface_self_action_approval_backend"
DESKTOP_SURFACE_SELF_ACTION_APPROVAL_BACKEND_MODE = "desktop_surface_self_action_approval_backend_in_process"
DESKTOP_SURFACE_SELF_ACTION_APPROVAL_BACKEND_ROLLBACK = (
    "remove_runtime_self_action_approval_backend_attr_to_use_current_facades"
)


@dataclass(frozen=True, slots=True)
class DesktopSelfActionApprovalCommand:
    request: DesktopSelfActionApprovalPayload
    checked_at: str


class DesktopSelfActionApprovalBackend(Protocol):
    mode: str

    async def approve(self, runtime: Any, command: DesktopSelfActionApprovalCommand) -> dict[str, Any]:
        ...


@dataclass(frozen=True, slots=True)
class DesktopSelfActionApprovalBackendReadiness:
    service_id: str
    mode: str
    ready: bool
    state_owner: str
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


class InProcessDesktopSelfActionApprovalBackend:
    mode = DESKTOP_SURFACE_SELF_ACTION_APPROVAL_BACKEND_MODE

    async def approve(self, runtime: Any, command: DesktopSelfActionApprovalCommand) -> dict[str, Any]:
        request = command.request
        pending_item = resolve_in_process_desktop_self_action_pending_item(runtime, request.queue_id)
        result = await self_action_approval.decide_desktop_self_action_approval(
            runtime.xinyu_dir,
            request,
            checked_at=command.checked_at,
            decide_approval_func=decide_self_action_approval,
            to_thread_func=asyncio.to_thread,
        )

        async def attach_patch_executor(
            patch_result: dict[str, Any],
            *,
            checked_at: str,
            authorize_codex: bool,
            timeout_seconds: int,
        ) -> None:
            await attach_in_process_desktop_self_action_patch_executor(
                runtime,
                patch_result,
                checked_at=checked_at,
                authorize_codex=authorize_codex,
                timeout_seconds=timeout_seconds,
            )

        return await self_action_approval.dispatch_desktop_self_action_approval_result(
            result,
            request,
            pending_item,
            checked_at=command.checked_at,
            attach_patch_executor_func=attach_patch_executor,
            snapshot_func=runtime.desktop_snapshot,
            approval_reply_func=compose_in_process_desktop_self_action_approval_reply,
            safe_str_func=_safe_str,
        )


DEFAULT_DESKTOP_SELF_ACTION_APPROVAL_BACKEND = InProcessDesktopSelfActionApprovalBackend()


def desktop_self_action_approval_backend_for_runtime(
    runtime: Any,
    *,
    explicit_backend: DesktopSelfActionApprovalBackend | None = None,
) -> DesktopSelfActionApprovalBackend:
    if explicit_backend is not None:
        return explicit_backend
    runtime_backend = getattr(runtime, DESKTOP_SURFACE_SELF_ACTION_APPROVAL_BACKEND_RUNTIME_ATTR, None)
    if runtime_backend is not None:
        return runtime_backend
    return DEFAULT_DESKTOP_SELF_ACTION_APPROVAL_BACKEND


async def execute_desktop_self_action_approval(
    runtime: Any,
    request: DesktopSelfActionApprovalPayload,
    *,
    checked_at: str,
    explicit_backend: DesktopSelfActionApprovalBackend | None = None,
) -> dict[str, Any]:
    backend = desktop_self_action_approval_backend_for_runtime(runtime, explicit_backend=explicit_backend)
    command = DesktopSelfActionApprovalCommand(request=request, checked_at=checked_at)
    return await backend.approve(runtime, command)


def desktop_self_action_approval_backend_readiness(
    runtime: Any,
    *,
    explicit_backend: DesktopSelfActionApprovalBackend | None = None,
) -> DesktopSelfActionApprovalBackendReadiness:
    backend = desktop_self_action_approval_backend_for_runtime(runtime, explicit_backend=explicit_backend)
    return DesktopSelfActionApprovalBackendReadiness(
        service_id="desktop_surface",
        mode=getattr(backend, "mode", type(backend).__name__),
        ready=True,
        state_owner=DESKTOP_SURFACE_STATE_OWNER,
        fallback_adapter=DESKTOP_SURFACE_FALLBACK_ADAPTER,
        rollback=DESKTOP_SURFACE_SELF_ACTION_APPROVAL_BACKEND_ROLLBACK,
        notes=(
            "self_action_approval_backend_contract_ready",
            "default_backend_uses_current_in_process_facades",
            "route_can_use_runtime_backend_attr",
            f"surface_rollback={DESKTOP_SURFACE_ROLLBACK}",
        ),
    )


async def attach_in_process_desktop_self_action_patch_executor(
    runtime: Any,
    result: dict[str, Any],
    *,
    checked_at: str,
    authorize_codex: bool,
    timeout_seconds: int,
    run_patch_executor_func: Callable[..., dict[str, Any]] = run_self_action_patch_executor,
    to_thread_func: self_action_approval.ToThreadFunc = asyncio.to_thread,
    safe_str_func: self_action_approval.SafeStrFunc = _safe_str,
) -> None:
    await self_action_approval.attach_desktop_self_action_patch_executor(
        runtime,
        result,
        checked_at=checked_at,
        authorize_codex=authorize_codex,
        timeout_seconds=timeout_seconds,
        run_patch_executor_func=run_patch_executor_func,
        to_thread_func=to_thread_func,
        safe_str_func=safe_str_func,
    )


def resolve_in_process_desktop_self_action_pending_item(
    runtime: Any,
    queue_id: str,
    *,
    list_approvals_func: Callable[..., dict[str, Any]] = list_self_action_approvals,
    safe_str_func: self_action_approval.SafeStrFunc = _safe_str,
) -> dict[str, Any]:
    listed = list_approvals_func(runtime.xinyu_dir)
    return self_action_approval.resolve_desktop_self_action_pending_item(
        listed,
        queue_id,
        safe_str_func=safe_str_func,
    )


def compose_in_process_desktop_self_action_approval_reply(result: dict[str, Any], *, decision: str) -> str:
    return compose_self_action_decision_reply(result, decision=decision)
