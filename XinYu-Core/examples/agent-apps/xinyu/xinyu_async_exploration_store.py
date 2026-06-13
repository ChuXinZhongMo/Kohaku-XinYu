from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_text
from state_service import read_text_safe


def read_async_exploration_text(path: Path) -> str:
    return read_text_safe(path)


def read_async_exploration_report_text(path: Path) -> tuple[str, str]:
    if not path.exists():
        return "missing_report", ""
    try:
        return "ok", path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return "unreadable_report", ""


def write_async_exploration_text(path: Path, text: str) -> None:
    atomic_write_text(path, text.rstrip())


def append_async_exploration_jsonl(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)
