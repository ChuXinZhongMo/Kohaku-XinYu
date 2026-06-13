from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_text
from state_service import read_text_safe


def read_watched_source_text(path: Path) -> str:
    return read_text_safe(Path(path), default="")


def write_watched_source_text(path: Path, text: str) -> None:
    atomic_write_text(Path(path), text.rstrip(), final_newline=True)


def append_watched_source_trace(path: Path, payload: dict[str, Any]) -> None:
    append_jsonl(Path(path), payload, sort_keys=True)
