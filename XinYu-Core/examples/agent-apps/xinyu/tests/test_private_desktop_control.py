from __future__ import annotations

import json
from pathlib import Path

import xinyu_private_ecosystem_grants as grants_mod
from xinyu_private_desktop_control import (
    ACTIONS_REL,
    boundaries_dict,
    build_desktop_snapshot,
    classify_desktop_action,
    evaluate_desktop_action,
    run_desktop_action,
)
from xinyu_private_desktop_service import SimulatedDesktopBackend


def _grant(root: Path, **fields) -> dict:
    base = {"private_desktop": {"enabled": True, "observe_only": True, **fields}}
    grants_mod.save_grants_patch(root, base)
    return grants_mod.desktop_grant(grants_mod.load_grants(root))


# 1. safe defaults disabled
def test_safe_defaults_disabled(tmp_path: Path) -> None:
    grant = grants_mod.desktop_grant(grants_mod.load_grants(tmp_path))
    assert grant["enabled"] is False
    assert grant["observe_only"] is True
    assert grant["single_step_actions"] is False
    assert grant["shell_enabled"] is False
    assert grant["network_enabled"] is False


# 2. observe blocked without grant
def test_observe_blocked_without_grant(tmp_path: Path) -> None:
    out = run_desktop_action(tmp_path, action_kind="status", execute=True, backend=SimulatedDesktopBackend())
    assert out["ok"] is False
    assert out["decision"]["reason"] == "desktop_grant_disabled"


# 3. observe allowed with isolated desktop grant
def test_observe_allowed_with_grant(tmp_path: Path) -> None:
    grant = _grant(tmp_path)
    out = run_desktop_action(tmp_path, action_kind="status", grant=grant, execute=True, backend=SimulatedDesktopBackend())
    assert out["ok"] is True
    assert out["result"] == "simulated"


# 4. click/type/hotkey blocked without approval
def test_single_step_blocked_without_approval(tmp_path: Path) -> None:
    # observe_only mode blocks actions entirely
    grant = _grant(tmp_path)
    for kind in ("click", "type_text", "hotkey"):
        out = run_desktop_action(tmp_path, action_kind=kind, grant=grant, execute=True, backend=SimulatedDesktopBackend())
        assert out["ok"] is False
        assert out["decision"]["reason"] == "observe_only_blocks_actions"
    # not observe_only but no approval / no single-step grant -> approval_required
    grant = _grant(tmp_path, observe_only=False)
    out = run_desktop_action(tmp_path, action_kind="click", x=10, y=10, grant=grant, execute=True, backend=SimulatedDesktopBackend())
    assert out["ok"] is False
    assert out["decision"]["reason"] == "approval_required"


def test_single_step_allowed_with_approval(tmp_path: Path) -> None:
    grant = _grant(tmp_path, observe_only=False)
    out = run_desktop_action(
        tmp_path, action_kind="click", x=10, y=10, grant=grant, approved=True, execute=True, backend=SimulatedDesktopBackend()
    )
    assert out["ok"] is True
    assert out["result"] == "simulated"


# 5. shell/download/install/network blocked in first landing
def test_high_risk_blocked_first_landing(tmp_path: Path) -> None:
    grant = _grant(tmp_path, observe_only=False, single_step_actions=True)
    for kind in ("shell", "download", "upload", "install_package", "network_open_external", "multi_step_task", "arbitrary_keyboard_mouse"):
        out = run_desktop_action(tmp_path, action_kind=kind, grant=grant, approved=True, execute=True, backend=SimulatedDesktopBackend())
        assert out["ok"] is False
        assert out["decision"]["reason"] == "high_risk_blocked_first_landing"
        assert out["decision"]["risk"] == "high_blocked"


# 6. actions write typed records
def test_actions_write_typed_records(tmp_path: Path) -> None:
    grant = _grant(tmp_path)
    run_desktop_action(tmp_path, action_kind="status", grant=grant, execute=True, backend=SimulatedDesktopBackend())
    lines = (tmp_path / ACTIONS_REL).read_text(encoding="utf-8-sig").strip().splitlines()
    record = json.loads(lines[-1])
    for key in ("action_id", "session_id", "action_kind", "risk", "result", "coordinate_plane", "target", "last_action_marker", "observed_at"):
        assert key in record
    assert record["action_id"].startswith("dact-")


# 7. simulated backend reports simulated, not live
def test_simulated_backend_reports_simulated(tmp_path: Path) -> None:
    backend = SimulatedDesktopBackend()
    assert backend.mode == "simulated"
    assert backend.status()["live"] is False
    grant = _grant(tmp_path)
    out = run_desktop_action(tmp_path, action_kind="screenshot", grant=grant, execute=True, backend=backend)
    assert out["backend"] == "simulated"
    assert out["result"] == "simulated"


# 8. frame refs are private-ecosystem relative paths only
def test_frame_refs_are_relative_private_paths(tmp_path: Path) -> None:
    grant = _grant(tmp_path)
    out = run_desktop_action(tmp_path, action_kind="screenshot", grant=grant, execute=True, backend=SimulatedDesktopBackend())
    ref = out["frame_ref"]
    assert ref.startswith("runtime/private_ecosystem/desktop_workspace/")
    assert ".." not in ref
    assert ":" not in ref  # no Windows drive / absolute path leaked


# 9. marker coordinates clamp to 0..1000
def test_marker_coordinates_clamp(tmp_path: Path) -> None:
    grant = _grant(tmp_path, observe_only=False)
    out = run_desktop_action(
        tmp_path, action_kind="click", x=99999, y=-50, grant=grant, approved=True, execute=True, backend=SimulatedDesktopBackend()
    )
    marker = out["record"]["last_action_marker"]
    assert marker["x"] == 1000
    assert marker["y"] == 0


# 10. no owner desktop capture appears anywhere
def test_no_owner_desktop_capture(tmp_path: Path) -> None:
    b = boundaries_dict()
    assert b["host_windows_desktop_controlled"] is False
    assert b["host_screen_captured"] is False
    assert b["owner_mouse_moved"] is False
    assert b["computer_control_enabled"] is False
    grant = _grant(tmp_path)
    run_desktop_action(tmp_path, action_kind="status", grant=grant, execute=True, backend=SimulatedDesktopBackend())
    snap = build_desktop_snapshot(tmp_path)
    assert snap["boundaries"]["host_screen_captured"] is False
    assert snap["boundaries"]["owner_mouse_moved"] is False


def test_classification_tiers() -> None:
    assert classify_desktop_action("status") == ("read_only", False)
    assert classify_desktop_action("propose_click") == ("proposal", False)
    assert classify_desktop_action("click") == ("approval_required", True)
    assert classify_desktop_action("shell") == ("high_blocked", True)
    assert classify_desktop_action("totally_unknown") == ("high_blocked", True)


def test_proposal_records_never_executes(tmp_path: Path) -> None:
    grant = _grant(tmp_path)
    out = run_desktop_action(
        tmp_path, action_kind="propose_click", x=5, y=5, grant=grant, approved=False, execute=True, backend=SimulatedDesktopBackend()
    )
    assert out["ok"] is True
    assert out["result"] == "proposed"
    assert out["record"]["risk"] == "proposal"


def test_evaluate_helper_direct() -> None:
    decision = evaluate_desktop_action("status", grant={"enabled": True, "observe_only": True})
    assert decision.ok is True and decision.risk == "read_only"
