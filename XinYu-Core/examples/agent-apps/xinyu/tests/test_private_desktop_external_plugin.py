from __future__ import annotations

from pathlib import Path

import pytest

import xinyu_private_ecosystem_grants as grants_mod
from xinyu_external_plugins import (
    ExternalCallContext,
    default_external_plugins,
    evaluate_external_call,
    external_plugin_runtime_allowed,
    save_external_plugin_control_patch,
)


@pytest.fixture(autouse=True)
def _force_simulated(monkeypatch) -> None:
    # Never touch real Docker in unit tests: force the honest simulated backend.
    monkeypatch.setattr("xinyu_private_desktop_service.docker_available", lambda *a, **k: False)


def test_private_desktop_registered() -> None:
    registry = default_external_plugins(env={})
    assert "xinyu_private_desktop" in registry
    spec = registry["xinyu_private_desktop"]
    assert spec.capabilities["status"].risk == "read_only"
    assert spec.capabilities["status"].proactive is True
    assert spec.capabilities["click"].requires_approval is True
    # High-risk capabilities are NOT registered in the first landing.
    for blocked in ("shell", "download", "install_package", "network_open_external"):
        assert blocked not in spec.capabilities


def test_read_only_requires_owner_private() -> None:
    registry = default_external_plugins(env={})
    blocked = evaluate_external_call(
        registry, "xinyu_private_desktop", "status",
        ExternalCallContext(source="t", owner_private=False, proactive=True, reason="look"),
    )
    assert blocked.ok is False and blocked.reason == "owner_private_required"
    ok = evaluate_external_call(
        registry, "xinyu_private_desktop", "status",
        ExternalCallContext(source="t", owner_private=True, proactive=True, reason="look"),
    )
    assert ok.ok is True


def test_single_step_requires_approval() -> None:
    registry = default_external_plugins(env={})
    decision = evaluate_external_call(
        registry, "xinyu_private_desktop", "click",
        ExternalCallContext(source="t", owner_private=True, approved=False, reason="x"),
    )
    assert decision.ok is False and decision.reason == "approval_required"


def test_proactive_blocked_for_single_step() -> None:
    registry = default_external_plugins(env={})
    decision = evaluate_external_call(
        registry, "xinyu_private_desktop", "click",
        ExternalCallContext(source="t", owner_private=True, proactive=True, reason="x"),
    )
    assert decision.ok is False and decision.reason == "proactive_not_allowed_for_capability"


# 11. external plugin disabled blocks runtime
def test_runtime_disabled_by_default(tmp_path: Path) -> None:
    allowed, reason, _ = external_plugin_runtime_allowed(tmp_path, "xinyu_private_desktop")
    assert allowed is False and reason == "plugin_disabled"


# 12. proactive disabled blocks proactive calls
def test_proactive_disabled_blocks_proactive(tmp_path: Path) -> None:
    save_external_plugin_control_patch(tmp_path, {"plugin_id": "xinyu_private_desktop", "enabled": True, "proactive_enabled": False})
    allowed, reason, _ = external_plugin_runtime_allowed(tmp_path, "xinyu_private_desktop", proactive=True)
    assert allowed is False and reason == "plugin_proactive_disabled"
    # non-proactive owner call is allowed once enabled+installed
    allowed2, reason2, _ = external_plugin_runtime_allowed(tmp_path, "xinyu_private_desktop", proactive=False)
    assert allowed2 is True and reason2 == "allowed"


def test_native_executor_status_observe(tmp_path: Path) -> None:
    from xinyu_bridge_external_plugin_routes import _execute_private_ecosystem_native

    grants_mod.save_grants_patch(tmp_path, {"private_desktop": {"enabled": True, "observe_only": True}})
    ctx = ExternalCallContext(source="t", owner_private=True, approved=False, reason="look")
    res = _execute_private_ecosystem_native(tmp_path, "xinyu_private_desktop", "status", {}, ctx)
    assert res["ok"] is True
    assert res["backend"] == "simulated"
    assert res["result"] == "simulated"


def test_native_executor_blocked_without_grant(tmp_path: Path) -> None:
    from xinyu_bridge_external_plugin_routes import _execute_private_ecosystem_native

    ctx = ExternalCallContext(source="t", owner_private=True, approved=False, reason="x")
    res = _execute_private_ecosystem_native(tmp_path, "xinyu_private_desktop", "status", {}, ctx)
    assert res["ok"] is False
    assert res["error_code"] == "desktop_grant_disabled"


def test_full_gate_chain_blocks_when_plugin_off(tmp_path: Path) -> None:
    from xinyu_bridge_external_plugin_routes import run_private_ecosystem_native_call

    # Grant enabled but plugin OFF -> chain blocks at runtime_allowed.
    grants_mod.save_grants_patch(tmp_path, {"private_desktop": {"enabled": True, "observe_only": True}})
    ctx = ExternalCallContext(source="t", owner_private=True, proactive=False, reason="look")
    res = run_private_ecosystem_native_call(tmp_path, "xinyu_private_desktop", "status", {}, ctx, execute=True)
    assert res["ok"] is False
    assert res["reason"] == "plugin_disabled"
