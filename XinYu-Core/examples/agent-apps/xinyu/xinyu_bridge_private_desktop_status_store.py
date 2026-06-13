from __future__ import annotations

from pathlib import Path


def private_desktop_status_path_exists(path: Path) -> bool:
    return Path(path).exists()


def private_desktop_status_path_mtime(path: Path) -> float:
    return Path(path).stat().st_mtime
