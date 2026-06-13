from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text


def write_promise_followup_state_text(path: Path, text: str) -> None:
    atomic_write_text(path, text)
