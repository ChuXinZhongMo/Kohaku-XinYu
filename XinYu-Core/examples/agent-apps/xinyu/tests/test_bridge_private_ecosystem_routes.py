from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any, Awaitable

import pytest

import xinyu_bridge_private_ecosystem_routes
import xinyu_private_ecosystem_grants as grants_mod
from xinyu_external_plugins import save_external_plugin_control_patch
from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_private_ecosystem_routes import (
    append_private_ecosystem_note,
    desktop_private_browser_action,
    desktop_private_browser_snapshot,
    desktop_private_ecosystem_grant,
    desktop_private_ecosystem_pause,
    desktop_private_ecosystem_snapshot,
    desktop_private_ecosystem_tick,
)
from xinyu_private_ecosystem import run_private_ecosystem_tick


def _run(coro: Awaitable[Any]) -> Any:
    # Drive the route coroutine in a dedicated thread with a fresh event loop.
    # The full suite can leave an ambient running loop in the main thread
    # (pytest-asyncio/anyio interaction), which would make a plain asyncio.run
    # raise "cannot be called from a running event loop". A worker thread has no
    # running loop, so this is robust regardless of collection order.
    box: dict[str, Any] = {}

    def runner() -> None:
        try:
            box["result"] = asyncio.run(coro)
        except BaseException as exc:  # noqa: BLE001 - re-raised on the caller thread
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


def test_append_private_ecosystem_note_records_disabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        xinyu_bridge_private_ecosystem_routes.grants_mod,
        "load_grants",
        lambda root: {"private_ecosystem": {"enabled": False}},
    )
    notes: list[str] = []
    runtime = FakeRuntime(tmp_path)
    runtime._trace_autonomous = lambda line: None  # type: ignore[attr-defined]

    append_private_ecosystem_note(runtime, notes, checked_at="2026-06-06T01:00:00+08:00")

    assert notes == ["private_ecosystem:disabled"]


def test_append_private_ecosystem_note_runs_enabled_tick(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        xinyu_bridge_private_ecosystem_routes.grants_mod,
        "load_grants",
        lambda root: {"private_ecosystem": {"enabled": True}},
    )

    def fake_tick(root, **kwargs):
        calls.append({"root": root, **kwargs})
        return {
            "selected_goal_id": "goal-1",
            "selected_action_kind": "browse",
            "action_status": "completed",
            "counters": {"ticks": 7},
        }

    monkeypatch.setattr(xinyu_bridge_private_ecosystem_routes, "run_private_ecosystem_tick", fake_tick)
    notes: list[str] = []
    runtime = FakeRuntime(tmp_path)
    runtime._trace_autonomous = lambda line: None  # type: ignore[attr-defined]

    append_private_ecosystem_note(runtime, notes, checked_at="2026-06-06T01:00:00+08:00")

    assert notes == ["private_ecosystem:goal-1/browse/completed/7"]
    assert calls == [
        {
            "root": tmp_path,
            "checked_at": "2026-06-06T01:00:00+08:00",
            "trigger": "autonomous_maintenance",
            "allow_send": True,
        }
    ]


def test_append_private_ecosystem_note_records_error(tmp_path: Path, monkeypatch) -> None:
    traces: list[str] = []

    def fake_load_grants(root):
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_private_ecosystem_routes.grants_mod, "load_grants", fake_load_grants)
    notes: list[str] = []
    runtime = FakeRuntime(tmp_path)
    runtime._trace_autonomous = traces.append  # type: ignore[attr-defined]

    append_private_ecosystem_note(runtime, notes, checked_at="2026-06-06T01:00:00+08:00")

    assert notes == ["private_ecosystem_error:RuntimeError"]
    assert traces and traces[0].startswith("private_ecosystem_error=RuntimeError")


def test_snapshot_route_returns_private_ecosystem(tmp_path: Path) -> None:
    run_private_ecosystem_tick(tmp_path, checked_at="2026-06-02T10:00:00+08:00", trigger="test")
    runtime = FakeRuntime(tmp_path)
    result = _run(desktop_private_ecosystem_snapshot(runtime, {}))
    assert result["ok"] is True
    assert result["privateEcosystem"]["observed"] is True


def test_pause_and_resume_kill_switch(tmp_path: Path) -> None:
    grants_mod.save_grants_patch(tmp_path, {"owner_private_autonomous_share": {"enabled": True, "paused": False}})
    runtime = FakeRuntime(tmp_path)

    paused = _run(desktop_private_ecosystem_pause(runtime, _owner_payload(action="pause")))
    assert paused["paused"] is True
    assert grants_mod.load_grants(tmp_path)["owner_private_autonomous_share"]["paused"] is True

    resumed = _run(desktop_private_ecosystem_pause(runtime, _owner_payload(action="resume")))
    assert resumed["paused"] is False
    assert grants_mod.share_active(grants_mod.load_grants(tmp_path)) is True


def test_grant_route_enables_browser(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    result = _run(
        desktop_private_ecosystem_grant(
            runtime, _owner_payload(grant={"private_browser": {"enabled": True, "read_only": True}})
        )
    )
    assert result["browser_enabled"] is True
    assert grants_mod.load_grants(tmp_path)["private_browser"]["enabled"] is True


def test_grant_route_uses_facade_sanitizer_monkeypatch(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_sanitize(patch_in):
        calls.append(patch_in)
        return {"private_browser": {"enabled": True, "read_only": True}}, ["custom.rejected"]

    monkeypatch.setattr(xinyu_bridge_private_ecosystem_routes, "_sanitize_grant_patch", fake_sanitize)
    runtime = FakeRuntime(tmp_path)

    result = _run(
        desktop_private_ecosystem_grant(runtime, _owner_payload(grant={"root_access": {"enabled": True}}))
    )

    assert calls == [{"root_access": {"enabled": True}}]
    assert result["browser_enabled"] is True
    assert result["rejected_keys"] == ["custom.rejected"]


def test_grant_route_enables_private_ecosystem_goal_loop(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    result = _run(
        desktop_private_ecosystem_grant(
            runtime, _owner_payload(grant={"private_ecosystem": {"enabled": True}})
        )
    )
    grants = grants_mod.load_grants(tmp_path)
    assert result["private_ecosystem_enabled"] is True
    assert grants["private_ecosystem"]["enabled"] is True
    assert grants["private_ecosystem"]["rollout_state"] == "observe_only"
    assert result["privateEcosystem"]["enabled"] is True


def test_private_ecosystem_tick_requires_enabled(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    result = _run(desktop_private_ecosystem_tick(runtime, _owner_payload()))
    assert result["accepted"] is False
    assert result["error"] == "private_ecosystem_disabled"


def test_private_ecosystem_tick_runs_enabled_goal(tmp_path: Path) -> None:
    grants_mod.save_grants_patch(
        tmp_path, {"private_ecosystem": {"enabled": True, "rollout_state": "observe_only"}}
    )
    runtime = FakeRuntime(tmp_path)
    result = _run(desktop_private_ecosystem_tick(runtime, _owner_payload()))
    assert result["accepted"] is True
    assert result["goalId"] != "none"
    assert result["actionStatus"] == "completed"
    assert result["privateEcosystem"]["enabled"] is True
    assert result["privateEcosystem"]["activeGoalId"] == result["goalId"]


def test_grant_route_rejects_unknown_section(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    with pytest.raises(BridgeRequestError):
        _run(desktop_private_ecosystem_grant(runtime, _owner_payload(grant={"root_access": {"enabled": True}})))


def test_non_owner_blocked(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path, owner=False)
    with pytest.raises(BridgeRequestError):
        _run(desktop_private_ecosystem_pause(runtime, {"action": "pause"}))


def _enable_browser_plugin(root: Path, *, proactive: bool = True) -> None:
    save_external_plugin_control_patch(
        root, {"plugin_id": "xinyu_private_browser", "enabled": True, "proactive_enabled": proactive}
    )


def test_browser_action_uses_facade_native_call_monkeypatch(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_native_call(root, *, action_kind: str, args: dict[str, object], approved: bool):
        calls.append({"root": root, "action_kind": action_kind, "args": args, "approved": approved})
        return {
            "ok": True,
            "result": "completed",
            "reason": "stubbed",
            "execution": {"engine": "stub_engine", "record": {"action": action_kind}},
            "decision": {"allowed": True},
        }

    monkeypatch.setattr(xinyu_bridge_private_ecosystem_routes, "_browser_action_via_plugin", fake_native_call)
    runtime = FakeRuntime(tmp_path)

    result = _run(
        desktop_private_browser_action(
            runtime,
            _owner_payload(
                action="snapshot_dom",
                approved="true",
                url=" https://example.com/news ",
                elementId="headline",
                value="unused",
            ),
        )
    )

    assert calls == [
        {
            "root": tmp_path,
            "action_kind": "snapshot_dom",
            "args": {
                "url": "https://example.com/news",
                "element_id": "headline",
                "value": "unused",
            },
            "approved": True,
        }
    ]
    assert result["ok"] is True
    assert result["engine"] == "stub_engine"
    assert result["record"] == {"action": "snapshot_dom"}


def test_browser_action_blocked_when_plugin_disabled(tmp_path: Path) -> None:
    # Grant enabled, but the external plugin is OFF -> the chain blocks it.
    grants_mod.save_grants_patch(tmp_path, {"private_browser": {"enabled": True, "read_only": True}})
    runtime = FakeRuntime(tmp_path)
    result = _run(
        desktop_private_browser_action(runtime, _owner_payload(action="snapshot_dom", url="https://example.com/news"))
    )
    assert result["ok"] is False
    assert result["reason"] == "plugin_disabled"


def test_browser_action_read_only_with_plugin_enabled(tmp_path: Path, monkeypatch) -> None:
    # Force the simulated path (offline, no real browser launch).
    monkeypatch.setattr(
        "xinyu_browser_engine_playwright.create_browser_engine",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no_engine_in_test")),
    )
    grants_mod.save_grants_patch(tmp_path, {"private_browser": {"enabled": True, "read_only": True}})
    _enable_browser_plugin(tmp_path)
    runtime = FakeRuntime(tmp_path)
    result = _run(
        desktop_private_browser_action(runtime, _owner_payload(action="snapshot_dom", url="https://example.com/news"))
    )
    assert result["ok"] is True
    assert result["result"] in {"simulated", "completed"}
    assert result["browser"]["actions_total"] >= 1


def test_browser_action_click_blocked_without_approval(tmp_path: Path) -> None:
    grants_mod.save_grants_patch(tmp_path, {"private_browser": {"enabled": True, "read_only": True}})
    _enable_browser_plugin(tmp_path)
    runtime = FakeRuntime(tmp_path)
    result = _run(
        desktop_private_browser_action(
            runtime, _owner_payload(action="click_element", url="https://example.com", element_id="b1")
        )
    )
    assert result["ok"] is False
    # Browser input actions are not registered until a real engine implements them.
    assert result["reason"] == "capability_not_registered"


def test_browser_action_invalid_kind(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    with pytest.raises(BridgeRequestError):
        _run(desktop_private_browser_action(runtime, _owner_payload(action="rm_rf")))


# -- grant route clamps / rejects (P0-2) ------------------------------------
def test_grant_clamps_share_limits(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    result = _run(
        desktop_private_ecosystem_grant(
            runtime,
            _owner_payload(
                grant={
                    "owner_private_autonomous_share": {
                        "enabled": True,
                        "daily_limit": 999,
                        "cooldown_minutes": 1,
                        "max_message_chars": 999999,
                    }
                }
            ),
        )
    )
    share = grants_mod.load_grants(tmp_path)["owner_private_autonomous_share"]
    assert share["daily_limit"] == 8
    assert share["cooldown_minutes"] == 30
    assert share["max_message_chars"] == 800
    assert result["accepted"] is True


def test_grant_rejects_empty_quiet_hours(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    with pytest.raises(BridgeRequestError):
        _run(
            desktop_private_ecosystem_grant(
                runtime, _owner_payload(grant={"owner_private_autonomous_share": {"quiet_hours": ""}})
            )
        )


def test_grant_rejects_browser_single_step(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    result = _run(
        desktop_private_ecosystem_grant(
            runtime, _owner_payload(grant={"private_browser": {"enabled": True, "single_step_actions": True}})
        )
    )
    assert "private_browser.single_step_actions" in result["rejected_keys"]
    assert grants_mod.load_grants(tmp_path)["private_browser"]["single_step_actions"] is False


def test_grant_rejects_computer_control(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    with pytest.raises(BridgeRequestError):
        _run(
            desktop_private_ecosystem_grant(
                runtime, _owner_payload(grant={"computer_control": {"enabled": True, "single_step_actions": True}})
            )
        )
    assert grants_mod.load_grants(tmp_path)["computer_control"]["enabled"] is False


def test_grant_rejects_unknown_key(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    result = _run(
        desktop_private_ecosystem_grant(
            runtime,
            _owner_payload(grant={"private_browser": {"enabled": True, "evil_key": 1}}),
        )
    )
    assert "private_browser.evil_key" in result["rejected_keys"]
    assert result["browser_enabled"] is True


def test_browser_snapshot_route(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    result = _run(desktop_private_browser_snapshot(runtime, {}))
    assert result["ok"] is True
    assert "engine" in result["browser"]


def test_grant_enables_private_desktop_observe_only(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    result = _run(
        desktop_private_ecosystem_grant(
            runtime, _owner_payload(grant={"private_desktop": {"enabled": True, "observe_only": True}})
        )
    )
    assert result["accepted"] is True
    grant = grants_mod.desktop_grant(grants_mod.load_grants(tmp_path))
    assert grant["enabled"] is True
    assert grant["observe_only"] is True


def test_grant_rejects_private_desktop_high_risk(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    result = _run(
        desktop_private_ecosystem_grant(
            runtime,
            _owner_payload(
                grant={
                    "private_desktop": {
                        "enabled": True,
                        "single_step_actions": True,
                        "shell_enabled": True,
                        "network_enabled": True,
                    }
                }
            ),
        )
    )
    for key in ("single_step_actions", "shell_enabled", "network_enabled"):
        assert f"private_desktop.{key}" in result["rejected_keys"]
    grant = grants_mod.desktop_grant(grants_mod.load_grants(tmp_path))
    assert grant["enabled"] is True
    assert grant["single_step_actions"] is False
    assert grant["shell_enabled"] is False
    assert grant["network_enabled"] is False
