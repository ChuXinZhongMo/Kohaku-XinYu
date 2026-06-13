from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_external_action_backend import (
    EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR,
    DryRunExternalActionExecutionBackend,
)
from xinyu_bridge_external_action_route_backend import maybe_execute_external_action_backend
from xinyu_bridge_external_plugin_routes import external_plugin_call, external_plugin_manifest
from xinyu_bridge_private_desktop_routes import desktop_private_desktop_start
from xinyu_bridge_private_desktop_routes import desktop_private_desktop_snapshot
from xinyu_bridge_utility_routes import package_install


def _runtime(root: Path, **extra: object) -> SimpleNamespace:
    values = {"xinyu_dir": root, "_closed": False, "_sessions": {}}
    values.update(extra)
    return SimpleNamespace(**values)


def test_external_action_route_backend_default_does_not_intercept(tmp_path: Path) -> None:
    result = asyncio.run(
        maybe_execute_external_action_backend(
            _runtime(tmp_path),
            {"plugin_id": "status"},
            route="/external/call",
            http_method="POST",
            runtime_method="external_plugin_call",
        )
    )

    assert result is None


def test_external_action_route_backend_enabled_returns_dry_run_response(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        **{EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR: DryRunExternalActionExecutionBackend(enabled=True)},
    )

    result = asyncio.run(
        maybe_execute_external_action_backend(
            runtime,
            {"plugin_id": "status", "query": {"trace": "route-backend"}},
            route="/external/call",
            http_method="POST",
            runtime_method="external_plugin_call",
        )
    )

    assert result is not None
    assert result["service_id"] == "external_action"
    assert result["status"] == "dry_run_ready"
    assert result["executed"] is False
    assert result["request"]["route"] == "/external/call"
    assert result["request"]["runtime_method"] == "external_plugin_call"
    assert result["request"]["payload"]["plugin_id"] == "status"
    assert result["request"]["query"] == {"trace": "route-backend"}


def test_external_plugin_call_uses_enabled_external_action_backend(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        **{EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR: DryRunExternalActionExecutionBackend(enabled=True)},
    )

    result = asyncio.run(external_plugin_call(runtime, {"plugin_id": "codex", "capability": "status"}))

    assert result["status"] == "dry_run_ready"
    assert result["request"]["route"] == "/external/call"
    assert result["request"]["runtime_method"] == "external_plugin_call"
    assert result["runtime_facade_present"] is False


def test_external_plugin_manifest_uses_enabled_external_action_backend(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        **{EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR: DryRunExternalActionExecutionBackend(enabled=True)},
    )

    result = asyncio.run(external_plugin_manifest(runtime, {"query": {"limit": "1"}}))

    assert result["status"] == "dry_run_ready"
    assert result["request"]["route"] == "/external/plugins"
    assert result["request"]["http_method"] == "GET"
    assert result["request"]["runtime_method"] == "external_plugin_manifest"
    assert result["request"]["query"] == {"limit": "1"}


def test_private_desktop_snapshot_get_uses_enabled_external_action_backend(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        **{EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR: DryRunExternalActionExecutionBackend(enabled=True)},
    )

    result = asyncio.run(desktop_private_desktop_snapshot(runtime, {"query": {"trace": "snapshot"}}))

    assert result["status"] == "dry_run_ready"
    assert result["request"]["route"] == "/desktop/private-desktop/snapshot"
    assert result["request"]["http_method"] == "GET"
    assert result["request"]["runtime_method"] == "desktop_private_desktop_snapshot"


def test_package_install_uses_enabled_external_action_backend_without_runtime_lock(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        **{EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR: DryRunExternalActionExecutionBackend(enabled=True)},
    )

    result = asyncio.run(package_install(runtime, {"text": "install pytest"}))

    assert result["status"] == "dry_run_ready"
    assert result["request"]["route"] == "/package/install"
    assert result["request"]["runtime_method"] == "package_install"
    assert result["request"]["payload"] == {"text": "install pytest"}


def test_private_desktop_start_keeps_owner_private_gate_before_backend(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        _owner_private_payload_matches=lambda payload: bool(payload.get("owner_private")),
        **{EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR: DryRunExternalActionExecutionBackend(enabled=True)},
    )

    with pytest.raises(BridgeRequestError, match="owner_private_context_required"):
        asyncio.run(desktop_private_desktop_start(runtime, {"owner_private": False}))

    result = asyncio.run(desktop_private_desktop_start(runtime, {"owner_private": True}))

    assert result["status"] == "dry_run_ready"
    assert result["request"]["route"] == "/desktop/private-desktop/start"
    assert result["request"]["owner_private_context"] is True
