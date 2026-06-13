from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text
from state_service import read_text_safe


def read_self_state_capsule_context_text(path: Path) -> str:
    return read_text_safe(path)


def write_self_state_capsule_state(path: Path, text: str) -> None:
    atomic_write_text(path, text)
