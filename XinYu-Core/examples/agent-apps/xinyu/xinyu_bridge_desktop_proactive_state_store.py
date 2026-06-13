from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_text


def append_desktop_proactive_history_jsonl(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)


def write_desktop_proactive_request_state_text(
    path: Path,
    text: str,
    *,
    final_newline: bool = True,
) -> None:
    atomic_write_text(path, text, final_newline=final_newline)
