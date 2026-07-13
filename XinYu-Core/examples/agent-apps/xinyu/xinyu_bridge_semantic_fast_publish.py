from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_runtime_presence import record_turn_finished
from xinyu_sent_reply_index import visible_text_hash


async def publish_semantic_fast_success_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    reply: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    total_elapsed_ms: int,
    notes: list[str],
    memory_changed: bool,
    record_route_stage_func: Callable[..., Any],
    timestamp_func: Callable[..., str],
) -> str:
    record_turn_finished(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply=reply,
        elapsed_ms=total_elapsed_ms,
        status="ok",
        notes=notes,
        memory_changed=memory_changed,
    )
    record_route_stage_func(
        runtime.xinyu_dir,
        turn_id=turn_id,
        stage="route_finished",
        route="owner_private_semantic_fast",
        status="ok",
        elapsed_ms=total_elapsed_ms,
        payload=payload,
        notes=notes[:8],
    )

    reply_hash = visible_text_hash(reply)
    await runtime._desktop_publish_chat_finished(
        payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
        started_at=timestamp_func(turn_started_wall),
        elapsed_ms=total_elapsed_ms,
        status="ok",
        notes=notes,
        memory_changed=memory_changed,
        archive_message_ids=[],
        reply_hash=reply_hash,
        recall_event_id="",
        recall_count=0,
        top_recall_sources=[],
    )
    return reply_hash
