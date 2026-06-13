from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_text
from state_service import read_json
from state_service import read_text_safe


def read_autonomous_outward_text(path: Path) -> str:
    return read_text_safe(path)


def read_autonomous_outward_json(path: Path, *, default: Any) -> Any:
    return read_json(path, default=default)


def read_autonomous_outward_jsonl_rows(path: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    rows.append(item)
    except OSError:
        return ()
    return tuple(rows)


def write_autonomous_outward_text(path: Path, text: str) -> None:
    atomic_write_text(path, text.rstrip())


def append_autonomous_outward_event(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)
