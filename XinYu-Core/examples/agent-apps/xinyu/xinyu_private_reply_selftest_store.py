from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_json
from state_service import read_text_safe


def read_private_reply_selftest_text(path: Path) -> str:
    return read_text_safe(path)


def write_private_reply_selftest_state(path: Path, state: dict[str, Any]) -> None:
    atomic_write_json(path, state, sort_keys=True)


def append_private_reply_selftest_trace(path: Path, state: dict[str, Any]) -> None:
    append_jsonl(path, state)
