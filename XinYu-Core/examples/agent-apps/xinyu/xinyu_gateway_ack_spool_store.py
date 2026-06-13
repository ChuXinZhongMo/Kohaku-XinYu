from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_text
from state_service import read_text_safe


def append_gateway_ack_spool_event(path: Path, event: dict[str, Any]) -> None:
    append_jsonl(Path(path), event, sort_keys=False)


def read_gateway_ack_spool_events(path: Path) -> tuple[list[dict[str, Any]], int]:
    lines = read_text_safe(Path(path), default="").splitlines()
    events: list[dict[str, Any]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            events.append(data)
    return events, len(lines)


def write_gateway_ack_spool_events(path: Path, events: list[dict[str, Any]]) -> None:
    content = "".join(
        json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
        for event in events
    )
    atomic_write_text(Path(path), content, final_newline=False)


def gateway_ack_spool_file_size(path: Path) -> int | None:
    try:
        return Path(path).stat().st_size
    except OSError:
        return None
