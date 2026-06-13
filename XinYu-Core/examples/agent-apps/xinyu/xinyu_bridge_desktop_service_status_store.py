from __future__ import annotations

from pathlib import Path


def desktop_service_path_exists(path: Path) -> bool:
    return Path(path).exists()
