from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_text
from state_service import read_text_safe


STATE_REL = Path("memory/context/uncertainty_pause_state.md")
TRACE_REL = Path("runtime/uncertainty_pause_trace.jsonl")


def uncertainty_pause_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STATE_REL


def uncertainty_pause_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / TRACE_REL


def read_uncertainty_pause_text(path: Path) -> str:
    return read_text_safe(path)


def write_uncertainty_pause_text(path: Path, text: str) -> None:
    atomic_write_text(path, text.rstrip())


def append_uncertainty_pause_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)
