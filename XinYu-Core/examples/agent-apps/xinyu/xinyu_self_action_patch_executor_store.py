from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_json
from state_service import atomic_write_text
from state_service import read_json
from state_service import read_text_safe


def read_self_action_patch_executor_json(path: Path, *, default: Any) -> Any:
    return read_json(path, default=default)


def read_self_action_patch_executor_text(path: Path, *, limit: int) -> str:
    text = read_text_safe(path)
    return text if len(text) <= limit else text[-limit:]


def write_self_action_patch_executor_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_json(path, data)


def write_self_action_patch_executor_text(path: Path, text: str) -> None:
    atomic_write_text(path, text)


def append_self_action_patch_executor_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)
