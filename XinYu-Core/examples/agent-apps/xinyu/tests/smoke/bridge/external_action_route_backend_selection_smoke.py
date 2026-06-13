from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

SMOKE_DIR = Path(__file__).resolve().parent
if str(SMOKE_DIR) not in sys.path:
    sys.path.insert(0, str(SMOKE_DIR))

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_external_action_backend import (
    EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR,
    DryRunExternalActionExecutionBackend,
)
from xinyu_bridge_external_plugin_routes import external_plugin_call, external_plugin_manifest
from xinyu_bridge_private_desktop_routes import desktop_private_desktop_snapshot
from xinyu_bridge_private_desktop_routes import desktop_private_desktop_start
from xinyu_bridge_utility_routes import package_install


def _check(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def _runtime(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        xinyu_dir=root,
        _closed=False,
        _sessions={},
        _owner_private_payload_matches=lambda payload: bool(payload.get("owner_private")),
        **{EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR: DryRunExternalActionExecutionBackend(enabled=True)},
    )


def _run_smoke() -> None:
    failures: list[str] = []
    root = Path(__file__).resolve().parents[3] / ".external-action-route-backend-smoke"
    root.mkdir(exist_ok=True)
    runtime = _runtime(root)

    plugin_result = asyncio.run(external_plugin_call(runtime, {"plugin_id": "codex", "capability": "status"}))
    _check(failures, plugin_result["status"] == "dry_run_ready", "external_plugin_call did not use backend")
    _check(failures, plugin_result["request"]["route"] == "/external/call", "external_plugin_call route changed")

    manifest_result = asyncio.run(external_plugin_manifest(runtime, {"query": {"trace": "manifest"}}))
    _check(failures, manifest_result["status"] == "dry_run_ready", "external_plugin_manifest did not use backend")
    _check(failures, manifest_result["request"]["route"] == "/external/plugins", "manifest route changed")
    _check(failures, manifest_result["request"]["http_method"] == "GET", "manifest method changed")

    snapshot_result = asyncio.run(desktop_private_desktop_snapshot(runtime, {"query": {"trace": "snapshot"}}))
    _check(failures, snapshot_result["status"] == "dry_run_ready", "private desktop snapshot did not use backend")
    _check(
        failures,
        snapshot_result["request"]["route"] == "/desktop/private-desktop/snapshot",
        "private desktop snapshot route changed",
    )

    package_result = asyncio.run(package_install(runtime, {"text": "install pytest"}))
    _check(failures, package_result["status"] == "dry_run_ready", "package_install did not use backend")
    _check(failures, package_result["request"]["route"] == "/package/install", "package_install route changed")

    try:
        asyncio.run(desktop_private_desktop_start(runtime, {"owner_private": False}))
    except BridgeRequestError as exc:
        _check(failures, exc.message == "owner_private_context_required", "owner-private rejection changed")
    else:
        failures.append("private desktop start bypassed owner-private gate")

    private_result = asyncio.run(desktop_private_desktop_start(runtime, {"owner_private": True}))
    _check(failures, private_result["status"] == "dry_run_ready", "private desktop start did not use backend")
    _check(
        failures,
        private_result["request"]["owner_private_context"] is True,
        "owner-private context was not preserved",
    )

    delattr(runtime, EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR)
    try:
        asyncio.run(desktop_private_desktop_start(runtime, {"owner_private": True}))
    except BridgeRequestError as exc:
        _check(failures, exc.message == "private_desktop_grant_disabled", "rollback did not reach in-process route")
    else:
        failures.append("runtime attr rollback did not restore in-process private desktop route")

    if failures:
        raise AssertionError("\n".join(failures))


def test_external_action_route_backend_selection_smoke() -> None:
    _run_smoke()


def main() -> int:
    try:
        _run_smoke()
    except AssertionError as exc:
        print("external_action_route_backend_selection_smoke failed")
        for failure in str(exc).splitlines():
            print(f"- {failure}")
        return 1
    print("external_action_route_backend_selection_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
