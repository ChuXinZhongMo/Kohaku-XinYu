from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_text


def append_early_visible_segment_shadow_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)


def write_early_visible_segment_shadow_state(path: Path, text: str) -> None:
    atomic_write_text(path, text)


def read_recent_early_visible_segment_shadow_rows(path: Path, *, max_rows: int) -> list[dict[str, Any]]:
    if max_rows <= 0 or not path.exists():
        return []
    rows: deque[dict[str, Any]] = deque(maxlen=max_rows)
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                if row.get("event_kind") != "early_visible_segment_shadow":
                    continue
                rows.append(row)
    except OSError:
        return []
    return list(rows)
