from __future__ import annotations

from pathlib import Path

from state_service import read_text_safe as _read_text_safe


def read_text_safe(path: Path, default: str = "") -> str:
    return _read_text_safe(path, default=default)
