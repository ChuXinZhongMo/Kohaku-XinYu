from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_text
from state_service import read_text_safe


def read_autonomous_self_exploration_text(path: Path) -> str:
    return read_text_safe(path)


def write_autonomous_self_exploration_text(path: Path, text: str) -> None:
    atomic_write_text(path, text.rstrip())


def append_autonomous_self_exploration_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)


def read_autonomous_self_exploration_trace_rows(path: Path) -> tuple[Any, ...]:
    rows: list[Any] = []
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return ()
    return tuple(rows)
