from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_values import safe_str as _safe_str


def build_slow_live_success_result(
    payload: dict[str, Any],
    *,
    reply: str,
    memory_changed: bool,
    turn_id: str,
    session_key: str,
    reply_hash: str,
    archive_message_ids: list[Any],
    archive_assistant_message_id: str | None = None,
    reply_bubble_force_units: list[Any],
    notes: list[str],
    safe_str_func: Callable[..., str] = _safe_str,
) -> dict[str, Any]:
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    assistant_message_id = archive_assistant_message_id
    if assistant_message_id is None:
        assistant_message_id = safe_str_func(archive_message_ids[-1] if archive_message_ids else "")
    return {
        "accepted": True,
        "reply": reply,
        "memory_changed": memory_changed,
        "turn_id": turn_id,
        "command_id": safe_str_func(metadata.get("desktop_command_id") or payload.get("command_id")),
        "session_id": session_key,
        "reply_hash": reply_hash,
        "archive_message_ids": archive_message_ids,
        "archive_assistant_message_id": assistant_message_id,
        "reply_bubble_force_units": reply_bubble_force_units,
        "notes": notes,
    }
