from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from xinyu_external_plugins import (
    ExternalCallContext,
    default_external_plugins,
    evaluate_external_call,
    external_plugin_runtime_allowed,
)


def test_private_browser_and_computer_registered() -> None:
    registry = default_external_plugins(env={})
    assert "xinyu_private_browser" in registry
    assert "xinyu_computer_control" in registry
    browser = registry["xinyu_private_browser"]
    assert set(browser.capabilities) == {
        "navigate",
        "navigate_readonly",
        "snapshot_dom",
        "screenshot",
        "extract_text",
    }
    assert browser.capabilities["snapshot_dom"].risk == "read_only"
    for unavailable in ("click_element", "fill", "press", "scroll", "wait_for_text", "download_file"):
        assert unavailable not in browser.capabilities

    computer = registry["xinyu_computer_control"]
    assert set(computer.capabilities) == {"screenshot", "region_screenshot"}
    for unavailable in ("click", "type_text", "hotkey", "propose_click"):
        assert unavailable not in computer.capabilities


def test_read_only_capability_requires_owner_private_then_allows() -> None:
    registry = default_external_plugins(env={})
    # Non-owner-private context is blocked.
    blocked = evaluate_external_call(
        registry,
        "xinyu_private_browser",
        "snapshot_dom",
        ExternalCallContext(source="t", owner_private=False, proactive=True, reason="look"),
    )
    assert blocked.ok is False
    assert blocked.reason == "owner_private_required"

    allowed = evaluate_external_call(
        registry,
        "xinyu_private_browser",
        "snapshot_dom",
        ExternalCallContext(source="t", owner_private=True, proactive=True, reason="look"),
    )
    assert allowed.ok is True


def test_unimplemented_computer_capability_is_not_registered() -> None:
    registry = default_external_plugins(env={})
    decision = evaluate_external_call(
        registry,
        "xinyu_computer_control",
        "click",
        ExternalCallContext(source="t", owner_private=True, approved=False, reason="x"),
    )
    assert decision.ok is False
    assert decision.reason == "capability_not_registered"


def test_unimplemented_browser_capability_is_not_registered() -> None:
    registry = default_external_plugins(env={})
    decision = evaluate_external_call(
        registry,
        "xinyu_private_browser",
        "click_element",
        ExternalCallContext(source="t", owner_private=True, proactive=True, reason="x"),
    )
    assert decision.ok is False
    assert decision.reason == "capability_not_registered"


def test_runtime_disabled_by_default(tmp_path: Path) -> None:
    allowed, reason, _ = external_plugin_runtime_allowed(tmp_path, "xinyu_private_browser")
    assert allowed is False
    assert reason == "plugin_disabled"
    allowed_c, reason_c, _ = external_plugin_runtime_allowed(tmp_path, "xinyu_computer_control")
    assert allowed_c is False
    assert reason_c == "plugin_disabled"


def test_native_executor_browser_read_only(tmp_path: Path) -> None:
    import xinyu_private_ecosystem_grants as g
    from xinyu_bridge_external_plugin_routes import _execute_private_ecosystem_native

    g.save_grants_patch(tmp_path, {"private_browser": {"enabled": True, "read_only": True}})
    ctx = ExternalCallContext(source="t", owner_private=True, approved=False, reason="x")
    res = _execute_private_ecosystem_native(
        tmp_path, "xinyu_private_browser", "snapshot_dom", {"url": "https://example.com/news"}, ctx
    )
    assert res["ok"] is True
    assert res["result"] in {"simulated", "completed"}


def test_native_executor_computer_blocked_without_grant(tmp_path: Path) -> None:
    from xinyu_bridge_external_plugin_routes import _execute_private_ecosystem_native

    ctx = ExternalCallContext(source="t", owner_private=True, approved=False, reason="x")
    res = _execute_private_ecosystem_native(tmp_path, "xinyu_computer_control", "screenshot", {}, ctx)
    assert res["ok"] is False
    assert res["error_code"] == "computer_control_grant_disabled"


def test_native_executor_computer_region_screenshot_passes_region(tmp_path: Path, monkeypatch) -> None:
    import xinyu_private_ecosystem_grants as g
    from xinyu_bridge_external_plugin_routes import _execute_private_ecosystem_native

    monkeypatch.setitem(
        sys.modules,
        "xinyu_computer_capture_mss",
        SimpleNamespace(MssCaptureBackend=lambda: (_ for _ in ()).throw(RuntimeError("no_capture"))),
    )
    g.save_grants_patch(tmp_path, {"computer_control": {"enabled": True, "observe_only": True}})
    ctx = ExternalCallContext(source="t", owner_private=True, approved=False, reason="look")
    region = {"x": 10, "y": 20, "width": 300, "height": 200}
    res = _execute_private_ecosystem_native(
        tmp_path, "xinyu_computer_control", "region_screenshot", {"region": region}, ctx
    )
    assert res["ok"] is True
    assert res["record"]["target"]["region"] == region


def test_native_executor_computer_rejects_unregistered_control(tmp_path: Path) -> None:
    from xinyu_bridge_external_plugin_routes import _execute_private_ecosystem_native

    ctx = ExternalCallContext(source="t", owner_private=True, approved=True, reason="x")
    res = _execute_private_ecosystem_native(tmp_path, "xinyu_computer_control", "click", {}, ctx)
    assert res["ok"] is False
    assert res["error_code"] == "computer_control_capability_unavailable"
