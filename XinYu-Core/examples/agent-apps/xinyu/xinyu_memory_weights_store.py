from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text


STATE_REL = "memory/context/memory_weight_state.md"


def memory_weight_state_path(root: Path) -> Path:
    return Path(root) / STATE_REL


def memory_weight_spec_path(root: Path, rel: str) -> Path:
    return Path(root) / rel


def read_memory_weight_text(path: Path) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


def read_memory_weight_state(root: Path) -> str:
    return read_memory_weight_text(memory_weight_state_path(root)) or ""


def write_memory_weight_state(root: Path, text: str) -> None:
    atomic_write_text(memory_weight_state_path(root), text, final_newline=False)
