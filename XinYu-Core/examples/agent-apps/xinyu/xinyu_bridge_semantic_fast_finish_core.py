from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_semantic_fast_finish_core_guard import prepare_semantic_fast_visible_reply
from xinyu_bridge_semantic_fast_finish_core_publish_result import publish_semantic_fast_finish_result


async def finish_owner_private_semantic_fast_turn_impl(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session: Any | None,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    semantic_started_at: float,
    before_memory: dict[str, Any] | None,
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
    decision: dict[str, Any],
    rendered_reply: str,
    renderer_name: str,
    safe_str_func: Callable[..., str],
    timestamp_func: Callable[..., str],
    command_id_func: Callable[[dict[str, Any]], str],
    clock_func: Callable[[], float],
    visible_reply_func: Callable[..., tuple[str, Any, Any] | None],
    update_tail_func: Callable[..., Any],
    build_notes_func: Callable[..., list[str]],
    memory_changed_func: Callable[..., bool],
    publish_result_func: Callable[..., Any],
) -> dict[str, Any] | None:
    visible_reply = visible_reply_func(runtime, payload, text=text, rendered_reply=rendered_reply)
    if visible_reply is None:
        return None
    reply, guard_flags, visible_dedupe = visible_reply

    update_tail_func(runtime, payload, text=text, reply=reply, session=session)

    elapsed_ms = int((clock_func() - semantic_started_at) * 1000)
    total_elapsed_ms = int((clock_func() - turn_started_at) * 1000)
    intents = tuple(safe_str_func(intent) for intent in decision.get("intents", ()))
    notes = build_notes_func(
        runtime,
        payload,
        text=text,
        reply=reply,
        decision=decision,
        event_sidecar=event_sidecar,
        cleanup=cleanup,
        renderer_name=renderer_name,
        elapsed_ms=elapsed_ms,
        intents=intents,
        guard_flags=guard_flags,
        visible_dedupe_notes=visible_dedupe.notes,
        safe_str_func=safe_str_func,
    )
    memory_changed = memory_changed_func(runtime, before_memory, notes)

    return await publish_result_func(
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
        decision=decision,
        intents=intents,
        elapsed_ms=elapsed_ms,
        renderer_name=renderer_name,
        safe_str_func=safe_str_func,
        timestamp_func=timestamp_func,
        command_id_func=command_id_func,
    )


__all__ = [
    "finish_owner_private_semantic_fast_turn_impl",
    "prepare_semantic_fast_visible_reply",
    "publish_semantic_fast_finish_result",
]
