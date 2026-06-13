from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


DESKTOP_PROACTIVE_HISTORY_MAX = 20
DESKTOP_PROACTIVE_HISTORY_REL = Path("memory/context/proactive_request_history.jsonl")


def desktop_proactive_history_time(item: dict[str, Any], safe_str: Callable[..., str]) -> str:
    return safe_str(item.get("updatedAt") or item.get("handledAt") or item.get("createdAt"))


def build_desktop_proactive_history_item(
    item: dict[str, Any],
    *,
    now_iso: Callable[[], str] | None = None,
) -> dict[str, Any]:
    history_item = dict(item)
    if "handledAt" not in history_item:
        if now_iso is None:
            now_iso = lambda: datetime.now().astimezone().isoformat()
        history_item["handledAt"] = history_item.get("updatedAt") or now_iso()
    if "event_time" not in history_item:
        history_item["event_time"] = (
            history_item.get("handledAt") or history_item.get("updatedAt") or history_item.get("createdAt")
        )
    return history_item


def parse_desktop_proactive_history_jsonl(
    text: str,
    *,
    safe_str: Callable[..., str],
    history_max: int = DESKTOP_PROACTIVE_HISTORY_MAX,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in text.splitlines()[-history_max * 4 :]:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and safe_str(row.get("candidateId")):
            rows.append(row)
    return rows


def compact_desktop_proactive_history(
    rows: list[dict[str, Any]],
    *,
    safe_str: Callable[..., str],
    history_max: int = DESKTOP_PROACTIVE_HISTORY_MAX,
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        candidate_id = safe_str(row.get("candidateId"))
        if candidate_id:
            by_id[candidate_id] = dict(row)
    return sorted(by_id.values(), key=lambda item: desktop_proactive_history_time(item, safe_str))[-history_max:]
