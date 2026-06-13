from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_json
from state_service import atomic_write_text
from state_service import read_json
from state_service import read_text_safe


def read_self_chosen_goal_json(path: Path) -> Any:
    return read_json(path, default={})


def read_self_chosen_goal_text(path: Path, *, limit: int) -> str:
    text = read_text_safe(path)
    if len(text) <= limit:
        return text
    return text[-limit:]


def write_self_chosen_goal_state_json(path: Path, state: dict[str, Any]) -> None:
    atomic_write_json(path, state)


def write_self_chosen_goal_state_markdown(path: Path, text: str) -> None:
    atomic_write_text(path, text)


def append_self_chosen_goal_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)
