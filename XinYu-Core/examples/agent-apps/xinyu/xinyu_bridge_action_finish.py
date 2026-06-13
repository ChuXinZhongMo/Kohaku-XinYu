from __future__ import annotations

import time
from typing import Any, Callable


async def finish_action_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    reply: str,
    notes: list[str],
    record_status: str,
    memory_snapshot_func: Callable[[Any], dict[str, Any]],
    record_turn_finished_func: Callable[..., Any],
    visible_text_hash_func: Callable[[str], str],
    timestamp_or_now_iso_func: Callable[[Any], str],
    command_id_func: Callable[[dict[str, Any]], str],
    publish_status: str = "ok",
    extra_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    after_memory = memory_snapshot_func(runtime.memory_root)
    memory_changed = before_memory != after_memory
    elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
    record_turn_finished_func(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply=reply,
        elapsed_ms=elapsed_ms,
        status=record_status,
        notes=notes,
        memory_changed=memory_changed,
    )
    reply_hash = visible_text_hash_func(reply)
    await runtime._desktop_publish_chat_finished(
        payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
        started_at=timestamp_or_now_iso_func(turn_started_wall),
        elapsed_ms=elapsed_ms,
        status=publish_status,
        notes=notes,
        memory_changed=memory_changed,
        archive_message_ids=[],
        reply_hash=reply_hash,
        recall_event_id="",
        recall_count=0,
        top_recall_sources=[],
    )
    response = {
        "accepted": True,
        "reply": reply,
        "memory_changed": memory_changed,
        "turn_id": turn_id,
        "command_id": command_id_func(payload),
        "session_id": session_key,
        "reply_hash": reply_hash,
        "archive_message_ids": [],
        "archive_assistant_message_id": "",
    }
    if extra_response:
        response.update(extra_response)
    response["notes"] = notes
    return response
