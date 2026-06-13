from __future__ import annotations

from collections.abc import Callable
from typing import Any


SafeStrFunc = Callable[..., str]


async def publish_chat_started(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    started_at: str,
    active_sessions: int,
    chat_started_payload_func: Callable[..., dict[str, Any]],
) -> None:
    await runtime._desktop_publish_event(
        "chat.turn.started",
        chat_started_payload_func(
            runtime._desktop_turn_base(payload, session_key=session_key, turn_id=turn_id),
            text=text,
            text_preview=runtime._desktop_text_preview(text, limit=180),
            started_at=started_at,
            active_sessions=active_sessions,
        ),
        privacy=runtime._desktop_privacy_for_payload(payload),
    )


async def publish_chat_finished(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    reply: str,
    session_key: str,
    turn_id: str,
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
    chat_finished_payload_func: Callable[..., dict[str, Any]],
    chat_finished_severity_func: Callable[[str], str | None],
    safe_str_func: SafeStrFunc,
    visible_text_hash_func: Callable[[str], str],
) -> None:
    item = chat_finished_payload_func(
        runtime._desktop_turn_base(payload, session_key=session_key, turn_id=turn_id),
        text=text,
        reply=reply,
        text_preview=runtime._desktop_text_preview(text, limit=180),
        reply_preview=runtime._desktop_text_preview(reply, limit=220),
        started_at=started_at,
        finished_at=finished_at,
        elapsed_ms=elapsed_ms,
        status=status,
        notes=notes,
        memory_changed=memory_changed,
        archive_message_ids=archive_message_ids,
        reply_hash=reply_hash,
        recall_event_id=recall_event_id,
        recall_count=recall_count,
        top_recall_sources=top_recall_sources,
        safe_str_func=safe_str_func,
        visible_text_hash_func=visible_text_hash_func,
    )
    runtime._desktop_remember_turn(item)
    await runtime._desktop_publish_event(
        "chat.turn.finished",
        item,
        privacy=runtime._desktop_privacy_for_payload(payload),
        severity=chat_finished_severity_func(item["status"]),
    )
    runtime._maybe_enqueue_tts(
        payload,
        reply=reply,
        status=item["status"],
        reply_hash=item["replyHash"],
        session_key=session_key,
        turn_id=turn_id,
    )


async def publish_memory_recall(
    runtime: Any,
    payload: dict[str, Any],
    result: Any,
    *,
    session_key: str,
    turn_id: str,
    memory_recall_notes_func: Callable[..., list[str]],
    memory_recall_should_skip_func: Callable[[list[str] | tuple[str, ...]], bool],
    memory_recall_top_sources_func: Callable[..., list[str]],
    memory_recall_payload_func: Callable[..., dict[str, Any]],
    memory_recall_remember_item_func: Callable[..., dict[str, Any]],
    dedupe_func: Callable[[list[str]], list[str]],
    safe_str_func: SafeStrFunc,
) -> dict[str, Any]:
    notes = memory_recall_notes_func(result, safe_str_func=safe_str_func)
    if memory_recall_should_skip_func(notes):
        return {}

    raw_items = list(getattr(result, "items", ()) or ())
    items = [runtime._desktop_recall_item(item) for item in raw_items[:8]]
    query_text = safe_str_func(getattr(result, "query_text", ""))
    route_payload = runtime._desktop_memory_route_payload(getattr(result, "route_plan", None))
    event_payload = memory_recall_payload_func(
        runtime._desktop_turn_base(payload, session_key=session_key, turn_id=turn_id),
        status="used" if items else "empty",
        recall_turn_id=safe_str_func(getattr(result, "turn_id", "")),
        query_hash=runtime._desktop_hash(query_text),
        query_text=query_text,
        raw_item_count=len(raw_items),
        top_sources=memory_recall_top_sources_func(items, dedupe_func=dedupe_func, safe_str_func=safe_str_func),
        route_payload=route_payload,
        items=items,
        notes=notes,
    )
    event = await runtime._desktop_publish_event(
        "memory.recall.used",
        event_payload,
        privacy=runtime._desktop_privacy_for_payload(payload),
    )
    if event:
        runtime._desktop_remember_memory_event(
            memory_recall_remember_item_func(event, event_payload, safe_str_func=safe_str_func)
        )
    return event
