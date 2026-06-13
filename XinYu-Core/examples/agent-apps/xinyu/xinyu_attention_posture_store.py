from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xinyu_state_io import read_text
from xinyu_state_io import write_text_atomic


def read_attention_posture_text(path: Path) -> str:
    return read_text(path)


def write_attention_posture_text(path: Path, text: str) -> None:
    write_text_atomic(path, text)


def read_attention_life_event_trace_rows(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines:
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_attention_life_event_trace_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n"
    path.write_text(text, encoding="utf-8")
