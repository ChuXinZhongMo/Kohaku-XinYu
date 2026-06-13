from __future__ import annotations

from pathlib import Path


def read_private_desktop_frame_bytes(path: Path) -> bytes:
    return Path(path).read_bytes()
