from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text


def write_live_system_prompt_dump(root: Path, rel: Path, content: str) -> None:
    atomic_write_text(root / rel, content, final_newline=False)
