from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

SMOKE_DIR = Path(__file__).resolve().parent
if str(SMOKE_DIR) not in sys.path:
    sys.path.insert(0, str(SMOKE_DIR))

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_desktop_recent_routes import desktop_chat_recent, desktop_memory_recent
from xinyu_bridge_desktop_self_action_routes import desktop_self_action_approval
from xinyu_bridge_desktop_snapshot import desktop_snapshot
from xinyu_bridge_desktop_surface_route_backend import (
    DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR,
    DryRunDesktopSurfaceRouteBackend,
)


def _check(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def _runtime(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        xinyu_dir=root,
        _closed=False,
        _desktop_recent_turns=[{"id": "turn-1", "text": "hello"}],
        _desktop_recent_memory_events=[{"id": "memory-1", "summary": "saved"}],
        **{DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR: DryRunDesktopSurfaceRouteBackend(enabled=True)},
    )


def _run_smoke() -> None:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-desktop-surface-route-backend-") as tmp:
        root = Path(tmp)
        runtime = _runtime(root)

        snapshot = asyncio.run(desktop_snapshot(runtime, {"query": {"trace": "snapshot"}}))
        _check(failures, snapshot["status"] == "dry_run_ready", "desktop_snapshot did not use backend")
        _check(failures, snapshot["request"]["route"] == "/desktop/snapshot", "snapshot route changed")

        memory = asyncio.run(desktop_memory_recent(runtime, {"limit": 1}))
        _check(failures, memory["status"] == "dry_run_ready", "desktop_memory_recent did not use backend")
        _check(failures, memory["request"]["route"] == "/desktop/memory/recent", "memory route changed")

        approval = asyncio.run(
            desktop_self_action_approval(runtime, {"queueId": "approval-1", "decision": "deny"})
        )
        _check(failures, approval["status"] == "dry_run_ready", "self-action approval did not use backend")
        _check(
            failures,
            approval["request"]["route"] == "/desktop/self-action/approval",
            "self-action route changed",
        )

        delattr(runtime, DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR)
        fallback = asyncio.run(desktop_chat_recent(runtime, {"limit": 1}))
        _check(failures, fallback["items"] == [{"id": "turn-1", "text": "hello"}], "rollback missed recent turn")
        _check(
            failures,
            fallback["notes"] == ["desktop_chat_recent_v0_runtime_buffer"],
            "rollback did not restore in-process chat recent route",
        )

    if failures:
        raise AssertionError("\n".join(failures))


def test_desktop_surface_route_backend_selection_smoke() -> None:
    _run_smoke()


def main() -> int:
    try:
        _run_smoke()
    except AssertionError as exc:
        print("desktop_surface_route_backend_selection_smoke failed")
        for failure in str(exc).splitlines():
            print(f"- {failure}")
        return 1
    print("desktop_surface_route_backend_selection_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
