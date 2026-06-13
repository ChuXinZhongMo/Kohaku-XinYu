from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from xinyu_bridge_desktop_self_action_approval_backend import (
    DESKTOP_SURFACE_SELF_ACTION_APPROVAL_BACKEND_RUNTIME_ATTR,
    DesktopSelfActionApprovalCommand,
    attach_in_process_desktop_self_action_patch_executor,
    desktop_self_action_approval_backend_readiness,
    execute_desktop_self_action_approval,
    resolve_in_process_desktop_self_action_pending_item,
)
from xinyu_bridge_desktop_self_action_approval_payload import DesktopSelfActionApprovalPayload
from xinyu_bridge_desktop_self_action_routes import desktop_self_action_approval
from xinyu_serviceization_contracts import service_contract_by_id


class StubSelfActionApprovalBackend:
    mode = "stub_self_action_approval_backend"

    def __init__(self) -> None:
        self.calls: list[DesktopSelfActionApprovalCommand] = []

    async def approve(self, runtime: object, command: DesktopSelfActionApprovalCommand) -> dict[str, Any]:
        self.calls.append(command)
        request = command.request
        return {
            "accepted": True,
            "queue_id": request.queue_id,
            "decision": request.decision,
            "execute": request.execute,
            "authorize_codex": request.authorize_codex,
            "authorize_existing": request.authorize_existing,
            "checked_at": command.checked_at,
        }


def test_desktop_self_action_approval_backend_contract_matches_service_manifest() -> None:
    manifest = service_contract_by_id("desktop_surface")

    assert "xinyu_bridge_desktop_self_action_approval_backend.py" in manifest.contract_modules
    assert "tests/test_desktop_self_action_approval_backend.py" in manifest.validation_tests
    assert manifest.process_split_ready is True
    assert "Ready for a controlled desktop_surface split" in manifest.process_split_gate


def test_execute_desktop_self_action_approval_uses_explicit_backend() -> None:
    backend = StubSelfActionApprovalBackend()
    request = _approval_request(queue_id="approval-1")

    result = asyncio.run(
        execute_desktop_self_action_approval(
            SimpleNamespace(),
            request,
            checked_at="2026-06-09T10:00:00+08:00",
            explicit_backend=backend,
        )
    )

    assert result["queue_id"] == "approval-1"
    assert result["checked_at"] == "2026-06-09T10:00:00+08:00"
    assert backend.calls == [DesktopSelfActionApprovalCommand(request=request, checked_at="2026-06-09T10:00:00+08:00")]


def test_desktop_self_action_approval_route_uses_runtime_backend_after_payload_parse() -> None:
    backend = StubSelfActionApprovalBackend()
    runtime = SimpleNamespace(
        _closed=False,
        **{DESKTOP_SURFACE_SELF_ACTION_APPROVAL_BACKEND_RUNTIME_ATTR: backend},
    )

    result = asyncio.run(
        desktop_self_action_approval(
            runtime,
            {
                "queueId": "approval-2",
                "decision": "approve",
                "execute": True,
                "authorizeCodex": True,
                "authorizeExisting": True,
            },
        )
    )

    assert result["queue_id"] == "approval-2"
    assert result["decision"] == "approved"
    assert result["authorize_codex"] is True
    assert result["authorize_existing"] is True
    assert backend.calls[0].request.queue_id == "approval-2"


def test_self_action_approval_backend_readiness_reports_runtime_backend_mode() -> None:
    backend = StubSelfActionApprovalBackend()
    runtime = SimpleNamespace(**{DESKTOP_SURFACE_SELF_ACTION_APPROVAL_BACKEND_RUNTIME_ATTR: backend})

    readiness = desktop_self_action_approval_backend_readiness(runtime)

    assert readiness.service_id == "desktop_surface"
    assert readiness.mode == "stub_self_action_approval_backend"
    assert readiness.ready is True
    assert "self_action_approval_backend_contract_ready" in readiness.notes


def test_pending_item_resolution_uses_current_approval_queue_facade(tmp_path: Path) -> None:
    runtime = SimpleNamespace(xinyu_dir=tmp_path)

    def list_approvals(root: Path) -> dict[str, Any]:
        assert root == tmp_path
        return {
            "approval_queue": {"latest_pending_queue_id": "approval-2"},
            "items": [
                {"queue_id": "approval-1", "status": "pending_owner_approval"},
                {"queue_id": "approval-2", "status": "pending_owner_approval"},
            ],
        }

    assert resolve_in_process_desktop_self_action_pending_item(
        runtime,
        "latest",
        list_approvals_func=list_approvals,
    ) == {"queue_id": "approval-2", "status": "pending_owner_approval"}


def test_attach_patch_executor_uses_runtime_codex_facade(tmp_path: Path) -> None:
    calls: dict[str, Any] = {}

    async def codex_execute(payload: dict[str, Any]) -> dict[str, Any]:
        calls["codex_payload"] = payload
        return {"accepted": True, "notes": ["scheduled"]}

    def run_patch_executor(root: Path, **kwargs: Any) -> dict[str, Any]:
        calls["patch_root"] = root
        calls["patch_kwargs"] = kwargs
        return {
            "accepted": True,
            "status": "codex_scheduled",
            "codex_payload": {"text": "run this patch", "metadata": {"approval_id": "approval-3"}},
        }

    result: dict[str, Any] = {}
    runtime = SimpleNamespace(xinyu_dir=tmp_path, codex_execute=codex_execute)

    asyncio.run(
        attach_in_process_desktop_self_action_patch_executor(
            runtime,
            result,
            checked_at="2026-06-09T10:05:00+08:00",
            authorize_codex=True,
            timeout_seconds=120,
            run_patch_executor_func=run_patch_executor,
            to_thread_func=_call_sync,
        )
    )

    assert calls["patch_root"] == tmp_path
    assert calls["patch_kwargs"]["execution_level"] == "schedule_codex"
    assert calls["patch_kwargs"]["allow_codex"] is True
    assert calls["patch_kwargs"]["timeout_seconds"] == 120
    assert calls["codex_payload"]["metadata"]["approval_id"] == "approval-3"
    assert result["patch_executor"] == {"accepted": True, "status": "codex_scheduled"}
    assert result["codex_execution"] == {"accepted": True, "notes": ["scheduled"]}


def _approval_request(queue_id: str = "latest") -> DesktopSelfActionApprovalPayload:
    return DesktopSelfActionApprovalPayload(
        queue_id=queue_id,
        decision="approved",
        reason="",
        execute=True,
        decided_by="owner_desktop",
        authorize_codex=False,
        authorize_existing=False,
        timeout_seconds=1800,
    )


async def _call_sync(func: Any, *args: Any, **kwargs: Any) -> Any:
    return func(*args, **kwargs)
