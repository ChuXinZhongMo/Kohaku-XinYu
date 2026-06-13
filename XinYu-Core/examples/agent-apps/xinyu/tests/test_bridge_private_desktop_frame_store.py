from __future__ import annotations

from xinyu_bridge_private_desktop_frame import _read_frame_data_url
from xinyu_bridge_private_desktop_frame_store import read_private_desktop_frame_bytes


def test_private_desktop_frame_store_reads_bytes(tmp_path) -> None:
    path = tmp_path / "latest_frame.png"
    path.write_bytes(b"frame-bytes")

    assert read_private_desktop_frame_bytes(path) == b"frame-bytes"


def test_private_desktop_frame_data_url_uses_store_and_missing_fallback(tmp_path) -> None:
    path = tmp_path / "latest_frame.png"

    assert _read_frame_data_url(path) == ""

    path.write_bytes(b"frame")

    assert _read_frame_data_url(path) == "data:image/png;base64,ZnJhbWU="
