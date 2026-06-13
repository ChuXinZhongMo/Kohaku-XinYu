from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_text
from state_service import read_text_safe


def append_group_shadow_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)


def read_group_shadow_history_text(path: Path) -> str:
    return read_text_safe(path)


def write_group_shadow_history_text(path: Path, text: str) -> None:
    atomic_write_text(path, text)


def write_group_shadow_state(path: Path, text: str) -> None:
    atomic_write_text(path, text)
