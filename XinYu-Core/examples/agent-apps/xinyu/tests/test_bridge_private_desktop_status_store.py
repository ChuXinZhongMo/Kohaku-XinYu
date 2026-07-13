from __future__ import annotations

import time

from xinyu_bridge_private_desktop_status import _live_state_payload
from xinyu_bridge_stores import (
    private_desktop_status_path_exists,
    private_desktop_status_path_mtime,
)
from xinyu_private_desktop_control import LATEST_FRAME_REL


def test_private_desktop_status_store_reads_latest_frame_metadata(tmp_path) -> None:
    path = tmp_path / "runtime/private_ecosystem/desktop_workspace/latest_frame.png"

    assert private_desktop_status_path_exists(path) is False

    path.parent.mkdir(parents=True)
    path.write_bytes(b"frame")

    assert private_desktop_status_path_exists(path) is True
    assert isinstance(private_desktop_status_path_mtime(path), float)


def test_private_desktop_live_state_payload_preserves_latest_frame_fields(tmp_path, monkeypatch) -> None:
    latest = tmp_path / LATEST_FRAME_REL
    latest.parent.mkdir(parents=True)
    latest.write_bytes(b"frame")
    monkeypatch.setattr(time, "time", lambda: 100.0)
    monkeypatch.setattr(
        "xinyu_bridge_private_desktop_status.private_desktop_status_path_mtime",
        lambda _path: 90.0,
    )

    payload = _live_state_payload(
        tmp_path,
        {"backend": "simulated", "session_state": "stopped", "live": False},
        boundaries_func=lambda: {"owner_mouse_moved": False},
    )

    assert payload["has_latest_frame"] is True
    assert payload["frame_age_seconds"] == 10
    assert payload["boundaries"] == {"owner_mouse_moved": False}
