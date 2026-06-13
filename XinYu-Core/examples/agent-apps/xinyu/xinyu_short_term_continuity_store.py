from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_text


STATE_REL = Path("memory/context/short_term_continuity_state.md")
TRACE_REL = Path("runtime/short_term_continuity_trace.jsonl")


def short_term_continuity_state_path(root: Path) -> Path:
    return Path(root) / STATE_REL


def short_term_continuity_trace_path(root: Path) -> Path:
    return Path(root) / TRACE_REL


def write_short_term_continuity_state(root: Path, text: str) -> None:
    atomic_write_text(short_term_continuity_state_path(root), text, final_newline=False)


def append_short_term_continuity_trace(root: Path, row: dict[str, Any]) -> None:
    append_jsonl(short_term_continuity_trace_path(root), row, sort_keys=True)
