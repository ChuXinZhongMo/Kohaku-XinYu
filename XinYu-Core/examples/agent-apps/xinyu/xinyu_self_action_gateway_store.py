from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_json
from state_service import atomic_write_text
from state_service import read_json
from state_service import read_text_safe


def read_self_action_gateway_json(path: Path, *, default: Any) -> Any:
    return read_json(path, default=default)


def read_self_action_gateway_text(path: Path, *, limit: int) -> str:
    text = read_text_safe(path)
    return text if len(text) <= limit else text[-limit:]


def write_self_action_gateway_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_json(path, data)


def write_self_action_gateway_text(path: Path, text: str) -> None:
    atomic_write_text(path, text)


def append_self_action_gateway_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)


def read_self_action_gateway_jsonl_summary(path: Path) -> tuple[int, str]:
    rows = 0
    last = ""
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                rows += 1
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(data, dict):
                    last = str(data.get("event_kind") or data.get("status") or "")
    except OSError:
        return 0, ""
    return rows, last
