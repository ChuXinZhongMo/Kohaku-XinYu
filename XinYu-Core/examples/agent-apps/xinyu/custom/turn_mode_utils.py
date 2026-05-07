"""Shared helpers for reading Xinyu runtime turn mode from disk."""

from __future__ import annotations

from pathlib import Path


def read_turn_mode(root: Path) -> str:
    path = root / "memory/context/turn_mode_state.md"
    if not path.exists():
        return ""
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if line.startswith("- mode:"):
            return line.split(":", 1)[1].strip()
    return ""
