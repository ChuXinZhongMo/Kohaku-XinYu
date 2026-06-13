from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text


def write_proactive_request_state_text(
    path: Path,
    text: str,
    *,
    final_newline: bool = True,
) -> None:
    atomic_write_text(path, text, final_newline=final_newline)
