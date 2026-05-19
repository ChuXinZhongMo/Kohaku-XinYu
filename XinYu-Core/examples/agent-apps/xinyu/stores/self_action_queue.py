from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from stores.state_service import append_jsonl


BOUNDARY_ID = "stores/self_action_queue"
COMPATIBILITY_NOTE = "legacy memory/context physical path kept until callers finish migration"

APPROVAL_QUEUE_REL = Path("memory/context/self_action_gateway_approval_queue.jsonl")


def approval_queue_path(root: Path) -> Path:
    return Path(root) / APPROVAL_QUEUE_REL


def append_approval_queue_event(root: Path, event: dict[str, Any]) -> None:
    payload = dict(event)
    payload.setdefault("event_time", _event_time_for(payload))
    append_jsonl(approval_queue_path(root), payload)


def _event_time_for(event: dict[str, Any]) -> str:
    for key in ("event_time", "observed_at", "recorded_at", "created_at", "updated_at", "checked_at", "decided_at"):
        value = event.get(key)
        if value:
            return str(value)
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_approval_queue_rows(root: Path) -> list[tuple[int, dict[str, Any]]]:
    try:
        lines = approval_queue_path(root).read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []

    rows: list[tuple[int, dict[str, Any]]] = []
    for index, line in enumerate(lines):
        clean = line.strip()
        if not clean:
            continue
        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append((index, data))
    return rows


def read_approval_queue_events(root: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    events = [dict(row) for _, row in read_approval_queue_rows(root)]
    if limit is None:
        return events
    if limit <= 0:
        return []
    return events[-limit:]
