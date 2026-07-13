from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_slow_live_publish_payloads import (
    archive_message_ids_from_result,
    build_failed_turn_publish_kwargs,
    build_success_turn_publish_kwargs,
)
from xinyu_bridge_slow_live_result import build_slow_live_success_result
from xinyu_runtime_presence import record_turn_finished
from xinyu_sent_reply_index import visible_text_hash


async def publish_slow_live_failed_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session: Any,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    status: str,
    notes: list[str],
    recalled_context_event: dict[str, Any],
    recalled_context: Any,
    clock_func: Callable[[], float],
    timestamp_func: Callable[..., str],
    safe_str_func: Callable[..., str],
) -> int:
    if status == "timeout":
        try:
            session.agent.interrupt()
        except Exception:
            pass
    elapsed_ms = int((clock_func() - turn_started_at) * 1000)
    record_turn_finished(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply="",
        elapsed_ms=elapsed_ms,
        status=status,
        notes=notes,
    )
    publish_kwargs = build_failed_turn_publish_kwargs(
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        elapsed_ms=elapsed_ms,
        status=status,
        notes=notes,
        recalled_context_event=recalled_context_event,
        recall_count=runtime._desktop_recall_count(recalled_context),
        top_recall_sources=runtime._desktop_top_recall_sources(recalled_context),
        timestamp_func=timestamp_func,
        safe_str_func=safe_str_func,
    )
    await runtime._desktop_publish_chat_finished(payload, **publish_kwargs)
    return elapsed_ms


async def publish_slow_live_success_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    reply: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: Any,
    after_memory: Any,
    notes: list[str],
    archive_result: dict[str, Any],
    recalled_context_event: dict[str, Any],
    recalled_context: Any,
    reply_bubble_force_units: list[int],
    trace_route_stage: Callable[..., Any],
    clock_func: Callable[[], float],
    timestamp_func: Callable[..., str],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    post_cleanup = await runtime._cleanup_idle_sessions(preserve_keys={session_key})
    if post_cleanup["cleaned_sessions"]:
        notes.append(f"cleaned_extra_sessions:{post_cleanup['cleaned_sessions']}")
    memory_changed = before_memory != after_memory
    elapsed_ms = int((clock_func() - turn_started_at) * 1000)
    record_turn_finished(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply=reply,
        elapsed_ms=elapsed_ms,
        status="ok",
        notes=notes,
        memory_changed=memory_changed,
    )
    trace_route_stage(
        "route_finished",
        route="slow_live",
        status="ok",
        elapsed_ms=elapsed_ms,
        notes=notes[:8],
    )
    archive_message_ids = archive_message_ids_from_result(archive_result)
    assistant_message_id = safe_str_func(archive_message_ids[-1] if archive_message_ids else "")
    reply_hash = visible_text_hash(reply)
    publish_kwargs = build_success_turn_publish_kwargs(
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        elapsed_ms=elapsed_ms,
        notes=notes,
        memory_changed=memory_changed,
        archive_message_ids=archive_message_ids,
        reply_hash=reply_hash,
        recalled_context_event=recalled_context_event,
        recall_count=runtime._desktop_recall_count(recalled_context),
        top_recall_sources=runtime._desktop_top_recall_sources(recalled_context),
        timestamp_func=timestamp_func,
        safe_str_func=safe_str_func,
    )
    await runtime._desktop_publish_chat_finished(payload, **publish_kwargs)
    return build_slow_live_success_result(
        payload,
        reply=reply,
        memory_changed=memory_changed,
        turn_id=turn_id,
        session_key=session_key,
        reply_hash=reply_hash,
        archive_message_ids=archive_message_ids,
        archive_assistant_message_id=assistant_message_id,
        reply_bubble_force_units=reply_bubble_force_units,
        notes=notes,
        safe_str_func=safe_str_func,
    )
