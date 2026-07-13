from __future__ import annotations

import time
from typing import Any

from xinyu_bridge_action_support import command_id, timestamp_or_now_iso
from xinyu_bridge_memory_snapshot import memory_snapshot
from xinyu_runtime_presence import record_turn_finished
from xinyu_sent_reply_index import visible_text_hash


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
    publish_status: str = "ok",
    extra_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    after_memory = memory_snapshot(runtime.memory_root)
    memory_changed = before_memory != after_memory
    elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
    record_turn_finished(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply=reply,
        elapsed_ms=elapsed_ms,
        status=record_status,
        notes=notes,
        memory_changed=memory_changed,
    )
    reply_hash = visible_text_hash(reply)
    await runtime._desktop_publish_chat_finished(
        payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
        started_at=timestamp_or_now_iso(turn_started_wall),
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
        "command_id": command_id(payload),
        "session_id": session_key,
        "reply_hash": reply_hash,
        "archive_message_ids": [],
        "archive_assistant_message_id": "",
    }
    if extra_response:
        response.update(extra_response)
    response["notes"] = notes
    return response
