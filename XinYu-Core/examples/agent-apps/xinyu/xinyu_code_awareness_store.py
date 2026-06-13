from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_json
from state_service import atomic_write_text
from state_service import read_json
from state_service import read_text_safe


def read_source_snapshot(path: Path) -> Any:
    return read_json(path, default={})


def write_source_snapshot(path: Path, snapshot: dict[str, Any]) -> None:
    atomic_write_json(path, snapshot, sort_keys=True, indent=2)


def append_source_change_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)


def write_code_awareness_state(path: Path, text: str) -> None:
    atomic_write_text(path, text)


def read_code_awareness_state_text(path: Path) -> str:
    return read_text_safe(path)
