from __future__ import annotations

from collections.abc import Callable
from typing import Any


SafeStrFunc = Callable[..., str]


def chat_started_payload(
    base_payload: dict[str, Any],
    *,
    text: str,
    text_preview: str,
    started_at: str,
    active_sessions: int,
) -> dict[str, Any]:
    return {
        **base_payload,
        "startedAt": started_at,
        "textPreview": text_preview,
        "textChars": len(text),
        "activeSessions": active_sessions,
    }


def chat_finished_payload(
    base_payload: dict[str, Any],
    *,
    text: str,
    reply: str,
    text_preview: str,
    reply_preview: str,
    started_at: str,
    finished_at: str,
    elapsed_ms: int,
    status: str,
    notes: list[str] | tuple[str, ...] | None,
    memory_changed: bool,
    archive_message_ids: list[Any] | tuple[Any, ...] | None,
    reply_hash: str,
    recall_event_id: str,
    recall_count: int,
    top_recall_sources: list[str] | tuple[str, ...] | None,
    safe_str_func: SafeStrFunc,
    visible_text_hash_func: Callable[[str], str],
) -> dict[str, Any]:
    safe_notes = _nonempty_safe_strings(notes or (), limit=12, safe_str_func=safe_str_func)
    return {
        **base_payload,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "status": safe_str_func(status, "unknown") or "unknown",
        "latencyMs": max(0, int(elapsed_ms)),
        "textPreview": text_preview,
        "replyPreview": reply_preview,
        "textChars": len(text),
        "replyChars": len(reply),
        "memoryChanged": bool(memory_changed),
        "replyHash": reply_hash or (visible_text_hash_func(reply) if reply else ""),
        "archiveMessageIds": [safe_str_func(value) for value in list(archive_message_ids or [])[:8]],
        "recallEventId": safe_str_func(recall_event_id),
        "recallCount": max(0, int(recall_count)),
        "topRecallSources": [safe_str_func(source) for source in list(top_recall_sources or [])[:6]],
        "notes": safe_notes,
    }


def chat_finished_severity(status: str) -> str | None:
    if status == "error":
        return "error"
    if status == "timeout":
        return "warn"
    return None


def memory_recall_payload(
    base_payload: dict[str, Any],
    *,
    status: str,
    recall_turn_id: str,
    query_hash: str,
    query_text: str,
    raw_item_count: int,
    top_sources: list[str],
    route_payload: dict[str, Any],
    items: list[dict[str, Any]],
    notes: list[str],
) -> dict[str, Any]:
    return {
        **base_payload,
        "status": status,
        "recallTurnId": recall_turn_id,
        "queryHash": query_hash,
        "queryChars": len(query_text),
        "itemCount": raw_item_count,
        "topSources": top_sources,
        "selectedExperts": route_payload.get("selectedExperts", []),
        "currentTurnFacts": route_payload.get("currentTurnFacts", []),
        "route": route_payload,
        "items": items,
        "notes": notes[:8],
    }


def _nonempty_safe_strings(
    values: list[Any] | tuple[Any, ...],
    *,
    limit: int,
    safe_str_func: SafeStrFunc,
) -> list[str]:
    result: list[str] = []
    for value in values:
        text = safe_str_func(value)
        if not text:
            continue
        result.append(text)
        if len(result) >= limit:
            break
    return result
