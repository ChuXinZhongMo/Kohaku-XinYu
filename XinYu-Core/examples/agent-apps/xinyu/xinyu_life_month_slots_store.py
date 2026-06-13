from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text
from state_service import read_text_safe


LIFE_MONTH_SLOTS_REL = "memory/context/life_month_slots.md"
CURRENT_LIFE_MONTH_CONTEXT_REL = "memory/context/current_life_month_context.md"


def life_month_slots_path(root: Path) -> Path:
    return Path(root) / LIFE_MONTH_SLOTS_REL


def current_life_month_context_path(root: Path) -> Path:
    return Path(root) / CURRENT_LIFE_MONTH_CONTEXT_REL


def read_life_month_text(path: Path) -> str:
    return read_text_safe(Path(path), default="")


def write_current_life_month_context(root: Path, text: str) -> None:
    atomic_write_text(current_life_month_context_path(root), text, final_newline=False)
