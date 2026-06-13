from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_json
from state_service import read_json
from state_service import read_text_safe


def append_turn_route_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)


def write_turn_route_state(path: Path, row: dict[str, Any]) -> None:
    atomic_write_json(path, row)


def read_turn_route_state(path: Path) -> Any:
    return read_json(path, default={})


def read_turn_route_trace_text(path: Path) -> str:
    return read_text_safe(path)
