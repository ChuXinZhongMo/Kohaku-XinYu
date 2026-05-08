from __future__ import annotations

import json
from typing import Any


QQ_FORWARD_CONTEXT_MAX_MESSAGES = 12
QQ_FORWARD_CONTEXT_MAX_TEXT_CHARS = 5000


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def forward_raw_items(payload: Any) -> list[Any]:
    if payload is None:
        return []
    if isinstance(payload, str):
        stripped = payload.strip()
        if not stripped:
            return []
        try:
            return forward_raw_items(json.loads(stripped))
        except json.JSONDecodeError:
            return [stripped]
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("messages", "message", "content", "nodes", "node", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = forward_raw_items(value)
            if nested:
                return nested
        if isinstance(value, str) and value.strip().startswith(("[", "{")):
            nested = forward_raw_items(value)
            if nested:
                return nested
    if any(key in payload for key in ("sender", "user_id", "nickname", "message", "content", "raw_message")):
        return [payload]
    return []


def dedupe_forward_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in messages:
        key = (
            safe_str(item.get("message_id")).strip(),
            safe_str(item.get("sender_name") or item.get("user_id")).strip(),
            safe_str(item.get("text") or item.get("rich_summary") or item.get("raw_message")).strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
