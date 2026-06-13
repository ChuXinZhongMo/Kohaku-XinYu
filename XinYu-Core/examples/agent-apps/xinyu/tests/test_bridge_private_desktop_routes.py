from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any, Awaitable

import pytest

import xinyu_private_ecosystem_grants as grants_mod
from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_private_desktop_routes import (
    desktop_private_desktop_frame,
    desktop_private_desktop_live_state,
    desktop_private_desktop_observe,
    desktop_private_desktop_snapshot,
    desktop_private_desktop_start,
    desktop_private_desktop_stop,
)
from xinyu_private_desktop_control import run_desktop_action
from xinyu_private_desktop_service import SimulatedDesktopBackend


@pytest.fixture(autouse=True)
def _force_simulated(monkeypatch) -> None:
    monkeypatch.setattr("xinyu_private_desktop_service.docker_available", lambda *a, **k: False)


def _run(coro: Awaitable[Any]) -> Any:
    box: dict[str, Any] = {}

    def runner() -> None:
        try:
            box["result"] = asyncio.run(coro)
        except BaseException as exc:  # noqa: BLE001 - re-raised on caller thread
            box["error"] = exc

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    if "error" in box:
        raise box["error"]
    return box["result"]


class FakeRuntime:
    def __init__(self, root: Path, owner: bool = True) -> None:
        self.xinyu_dir = root
        self._owner = owner

    def _owner_private_payload_matches(self, payload: dict) -> bool:
        return self._owner


def _owner_payload(**extra) -> dict:
    base = {"metadata": {"is_owner_user": True}, "message_type": "private"}
    base.update(extra)
    return base


def test_snapshot_route(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    result = _run(desktop_private_desktop_snapshot(runtime, {}))
    assert result["ok"] is True
    snap = result["privateDesktop"]
    assert snap["boundaries"]["host_windows_desktop_controlled"] is False
    assert snap["backend"] in {"simulated", "unavailable"}


def test_live_state_route(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    result = _run(desktop_private_desktop_live_state(runtime, {}))
    assert result["ok"] is True
    assert result["live"] is False
    assert result["boundaries"]["owner_mouse_moved"] is False


# 13. owner-private required for start/stop routes
def test_start_requires_owner_private(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path, owner=False)
    with pytest.raises(BridgeRequestError):
        _run(desktop_private_desktop_start(runtime, {}))
    with pytest.raises(BridgeRequestError):
        _run(desktop_private_desktop_stop(runtime, {}))
    with pytest.raises(BridgeRequestError):
        _run(desktop_private_desktop_observe(runtime, {}))


def test_start_requires_private_desktop_grant(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    with pytest.raises(BridgeRequestError) as caught:
        _run(desktop_private_desktop_start(runtime, _owner_payload()))
    assert caught.value.status == 403
    assert caught.value.message == "private_desktop_grant_disabled"


def test_start_without_docker_reports_unavailable(tmp_path: Path) -> None:
    grants_mod.save_grants_patch(tmp_path, {"private_desktop": {"enabled": True, "observe_only": True}})
    runtime = FakeRuntime(tmp_path)
    result = _run(desktop_private_desktop_start(runtime, _owner_payload()))
    assert result["ok"] is False
    assert result["error_code"] == "docker_unavailable"


def test_stop_idempotent_without_docker(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    result = _run(desktop_private_desktop_stop(runtime, _owner_payload()))
    assert result["ok"] is True


def test_observe_route_records_read_only_action(tmp_path: Path) -> None:
    grants_mod.save_grants_patch(tmp_path, {"private_desktop": {"enabled": True, "observe_only": True}})
    runtime = FakeRuntime(tmp_path)
    result = _run(desktop_private_desktop_observe(runtime, _owner_payload()))
    assert result["ok"] is True
    assert result["accepted"] is True
    assert result["action"] == "screenshot"
    assert result["result"] == "simulated"
    snap = result["privateDesktop"]
    assert snap["last_action_kind"] == "screenshot"
    assert snap["last_result"] == "simulated"
    assert snap["boundaries"]["owner_mouse_moved"] is False


def test_observe_route_rejects_non_read_only_action(tmp_path: Path) -> None:
    grants_mod.save_grants_patch(tmp_path, {"private_desktop": {"enabled": True, "observe_only": True}})
    runtime = FakeRuntime(tmp_path)
    with pytest.raises(BridgeRequestError) as caught:
        _run(desktop_private_desktop_observe(runtime, _owner_payload(action="click")))
    assert caught.value.status == 400
    assert caught.value.message == "private_desktop_observe_read_only_only"


# 15. live frame route cannot path-traverse
def test_frame_route_rejects_traversal(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    for bad in ("../../etc/passwd", "..\\..\\secret", "sub/dir.png", "/abs/path.png", "frame.txt"):
        with pytest.raises(BridgeRequestError):
            _run(desktop_private_desktop_frame(runtime, {"frame_id": bad}))


def test_frame_route_serves_latest(tmp_path: Path) -> None:
    grant = grants_mod.desktop_grant(
        grants_mod.save_grants_patch(tmp_path, {"private_desktop": {"enabled": True, "observe_only": True}})
    )
    run_desktop_action(tmp_path, action_kind="screenshot", grant=grant, execute=True, backend=SimulatedDesktopBackend())
    runtime = FakeRuntime(tmp_path)
    result = _run(desktop_private_desktop_frame(runtime, {}))
    assert result["ok"] is True
    assert result["frame_data_url"].startswith("data:image/png;base64,")
    assert result["frame_ref"].startswith("runtime/private_ecosystem/desktop_workspace/")


def test_frame_route_accepts_valid_frame_id(tmp_path: Path) -> None:
    # A well-formed frame_id that does not exist yet returns has_frame False, not an error.
    runtime = FakeRuntime(tmp_path)
    result = _run(desktop_private_desktop_frame(runtime, {"frame_id": "dact-abc123.png"}))
    assert result["has_frame"] is False
