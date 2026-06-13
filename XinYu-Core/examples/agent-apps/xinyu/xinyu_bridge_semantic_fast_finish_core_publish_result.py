from __future__ import annotations

from collections.abc import Callable
from typing import Any


async def publish_semantic_fast_finish_result(
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
    decision: dict[str, Any],
    intents: tuple[str, ...],
    elapsed_ms: int,
    renderer_name: str,
    safe_str_func: Callable[..., str],
    timestamp_func: Callable[..., str],
    command_id_func: Callable[[dict[str, Any]], str],
    publish_success_func: Callable[..., Any],
    response_func: Callable[..., dict[str, Any]],
    record_finished_func: Callable[..., Any],
    record_route_stage_func: Callable[..., Any],
    visible_text_hash_func: Callable[[str], str],
) -> dict[str, Any]:
    reply_hash = await publish_success_func(
        runtime,
        payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        total_elapsed_ms=total_elapsed_ms,
        notes=notes,
        memory_changed=memory_changed,
        record_finished_func=record_finished_func,
        record_route_stage_func=record_route_stage_func,
        visible_text_hash_func=visible_text_hash_func,
        timestamp_func=timestamp_func,
    )
    return response_func(
        payload,
        reply=reply,
        memory_changed=memory_changed,
        turn_id=turn_id,
        session_key=session_key,
        reply_hash=reply_hash,
        decision=decision,
        intents=intents,
        elapsed_ms=elapsed_ms,
        renderer_name=renderer_name,
        notes=notes,
        safe_str_func=safe_str_func,
        command_id_func=command_id_func,
    )


__all__ = ["publish_semantic_fast_finish_result"]
