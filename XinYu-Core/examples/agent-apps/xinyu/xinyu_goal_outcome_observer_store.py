from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_json
from state_service import atomic_write_text
from state_service import read_json
from state_service import read_text_safe


def read_goal_outcome_json(path: Path, *, default: Any) -> Any:
    return read_json(path, default=default)


def read_goal_outcome_text(path: Path) -> str:
    return read_text_safe(path)


def append_goal_outcome_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)


def write_goal_outcome_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_json(path, data)


def write_goal_outcome_text(path: Path, text: str) -> None:
    atomic_write_text(path, text)


def read_goal_outcome_jsonl_summary(path: Path) -> dict[str, Any]:
    row_count = 0
    last_event = ""
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row_count += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    last_event = str(row.get("event_kind") or row.get("kind") or row.get("status") or "")
    except OSError:
        pass
    return {"row_count": row_count, "last_event_kind": last_event}


def read_goal_outcome_jsonl_rows(path: Path, *, max_rows: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
                    if len(rows) > max_rows:
                        rows.pop(0)
    except OSError:
        return []
    return rows
