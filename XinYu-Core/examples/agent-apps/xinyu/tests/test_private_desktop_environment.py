from __future__ import annotations

from pathlib import Path

from xinyu_private_desktop_environment import probe_desktop_environment


def test_probe_is_read_only_and_well_formed(tmp_path: Path) -> None:
    report = probe_desktop_environment(tmp_path)
    assert report["ok"] is True
    assert report["read_only"] is True
    assert report["installed_anything"] is False
    assert report["decision"] in {"available", "blocked_no_isolated_backend"}
    assert isinstance(report["backends_available"], list)
    assert isinstance(report["loopback_bind_ok"], bool)


def test_probe_never_implies_host_control(tmp_path: Path) -> None:
    b = probe_desktop_environment(tmp_path)["boundaries"]
    # The probe must never report host desktop control / capture / mouse moves.
    assert b["host_windows_desktop_controlled"] is False
    assert b["host_screen_captured"] is False
    assert b["owner_mouse_moved"] is False
    assert b["computer_control_enabled"] is False
    assert b["falls_back_to_host_automation"] is False


def test_blocked_when_no_backend(tmp_path: Path) -> None:
    report = probe_desktop_environment(tmp_path)
    if not report["backends_available"]:
        assert report["decision"] == "blocked_no_isolated_backend"
        assert report["blocker"]
        assert report["owner_action"]
    else:
        assert report["decision"] == "available"


def test_each_backend_reports_usable_bool(tmp_path: Path) -> None:
    report = probe_desktop_environment(tmp_path)
    for key in ("docker", "wsl", "hyperv"):
        assert isinstance(report[key]["usable"], bool)
