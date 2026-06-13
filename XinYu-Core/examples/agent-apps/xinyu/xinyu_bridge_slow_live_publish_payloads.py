from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_time_utils import timestamp_or_now_iso
from xinyu_bridge_values import safe_str as _safe_str


def archive_message_ids_from_result(archive_result: dict[str, Any]) -> list[Any]:
    return list(archive_result.get("message_ids", []))


def build_failed_turn_publish_kwargs(
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    elapsed_ms: int,
    status: str,
    notes: list[str],
    recalled_context_event: dict[str, Any],
    recall_count: int,
    top_recall_sources: list[Any],
    timestamp_func: Callable[..., str] = timestamp_or_now_iso,
    safe_str_func: Callable[..., str] = _safe_str,
) -> dict[str, Any]:
    return {
        "text": text,
        "reply": "",
        "session_key": session_key,
        "turn_id": turn_id,
        "started_at": timestamp_func(turn_started_wall),
        "elapsed_ms": elapsed_ms,
        "status": status,
        "notes": notes,
        "memory_changed": False,
        "recall_event_id": safe_str_func(recalled_context_event.get("id")),
        "recall_count": recall_count,
        "top_recall_sources": top_recall_sources,
    }


def build_success_turn_publish_kwargs(
    *,
    text: str,
    reply: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    elapsed_ms: int,
    notes: list[str],
    memory_changed: bool,
    archive_message_ids: list[Any],
    reply_hash: str,
    recalled_context_event: dict[str, Any],
    recall_count: int,
    top_recall_sources: list[Any],
    timestamp_func: Callable[..., str] = timestamp_or_now_iso,
    safe_str_func: Callable[..., str] = _safe_str,
) -> dict[str, Any]:
    return {
        "text": text,
        "reply": reply,
        "session_key": session_key,
        "turn_id": turn_id,
        "started_at": timestamp_func(turn_started_wall),
        "elapsed_ms": elapsed_ms,
        "status": "ok",
        "notes": notes,
        "memory_changed": memory_changed,
        "archive_message_ids": archive_message_ids,
        "reply_hash": reply_hash,
        "recall_event_id": safe_str_func(recalled_context_event.get("id")),
        "recall_count": recall_count,
        "top_recall_sources": top_recall_sources,
    }
