from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_json
from state_service import atomic_write_text
from state_service import read_json


def read_group_interest_state_json(path: Path) -> Any:
    return read_json(path, default={})


def write_group_interest_state_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_json(path, data, sort_keys=True, indent=2)


def write_group_interest_state_markdown(path: Path, text: str) -> None:
    atomic_write_text(path, text)


def append_group_interest_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)
