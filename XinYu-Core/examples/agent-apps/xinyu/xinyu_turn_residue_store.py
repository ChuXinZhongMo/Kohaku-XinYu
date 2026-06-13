from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text


STATE_REL = "memory/context/persona_surface_state.md"


def turn_residue_state_path(root: Path) -> Path:
    return Path(root) / STATE_REL


def read_turn_residue_state(root: Path) -> str | None:
    try:
        return turn_residue_state_path(root).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


def write_turn_residue_state(root: Path, text: str) -> None:
    atomic_write_text(turn_residue_state_path(root), text, final_newline=False)
