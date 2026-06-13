from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from state_service import append_jsonl
from state_service import atomic_write_text
from state_service import read_json
from state_service import read_text_safe


def read_action_feedback_coverage_text(path: Path) -> str:
    return read_text_safe(path)


def read_action_feedback_coverage_json(path: Path) -> dict[str, Any]:
    data = read_json(path, default={})
    return data if isinstance(data, dict) else {}


def latest_action_feedback_jsonl_row(
    path: Path,
    predicate: Callable[[dict[str, Any]], bool],
    *,
    max_lines: int = 400,
) -> dict[str, Any]:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return {}
    for line in reversed(lines[-max(1, int(max_lines)) :]):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and predicate(data):
            return data
    return {}


def write_action_feedback_coverage_text(path: Path, text: str) -> None:
    atomic_write_text(path, text.rstrip())


def append_action_feedback_coverage_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)
