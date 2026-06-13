from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_text
from state_service import read_text_safe


def read_learning_closed_loop_text(path: Path) -> str:
    return read_text_safe(path)


def write_learning_closed_loop_text(path: Path, text: str) -> None:
    atomic_write_text(path, text.rstrip())


def append_learning_closed_loop_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)
