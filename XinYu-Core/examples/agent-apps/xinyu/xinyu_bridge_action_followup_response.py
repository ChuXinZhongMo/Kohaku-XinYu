from __future__ import annotations

from typing import Any, Callable


def guarded_followup_reply(
    runtime: Any,
    payload: dict[str, Any],
    followup: dict[str, Any],
    *,
    text: str,
    safe_str_func: Callable[..., str],
) -> tuple[str, list[str] | tuple[str, ...]]:
    reply = safe_str_func(followup.get("reply")).strip()
    if not reply:
        return "", []
    guarded_reply, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=text,
        reply=reply,
    )
    if guarded_reply:
        reply = guarded_reply
    return reply, guard_flags


async def finish_followup_response(
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
    result_key: str,
    result_payload: dict[str, str],
    finish_action_turn_func: Callable[..., Any],
    memory_snapshot_func: Callable[[Any], dict[str, Any]],
    record_turn_finished_func: Callable[..., Any],
    visible_text_hash_func: Callable[[str], str],
    timestamp_or_now_iso_func: Callable[[Any], str],
    command_id_func: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    return await finish_action_turn_func(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        reply=reply,
        notes=notes,
        record_status="ok",
        memory_snapshot_func=memory_snapshot_func,
        record_turn_finished_func=record_turn_finished_func,
        visible_text_hash_func=visible_text_hash_func,
        timestamp_or_now_iso_func=timestamp_or_now_iso_func,
        command_id_func=command_id_func,
        extra_response={result_key: result_payload},
    )
