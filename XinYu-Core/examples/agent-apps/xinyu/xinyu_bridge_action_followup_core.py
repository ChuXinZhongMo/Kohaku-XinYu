from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from xinyu_bridge_action_followup_response import finish_followup_response, guarded_followup_reply
from xinyu_bridge_action_followup_status import followup_row, followup_status_notes


@dataclass(frozen=True)
class ActionFollowupSpec:
    intercept_note: str
    row_note_func: Callable[[dict[str, Any], Callable[..., str]], str]
    result_key: str
    result_payload_func: Callable[[dict[str, Any], dict[str, Any], Callable[..., str]], dict[str, str]]


async def handle_action_followup_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
    compose_followup_func: Callable[[Any, str], dict[str, Any] | None],
    spec: ActionFollowupSpec,
    finish_action_turn_func: Callable[..., Any],
    extend_common_finish_notes_func: Callable[..., None],
    memory_snapshot_func: Callable[[Any], dict[str, Any]],
    record_turn_finished_func: Callable[..., Any],
    visible_text_hash_func: Callable[[str], str],
    timestamp_or_now_iso_func: Callable[[Any], str],
    command_id_func: Callable[[dict[str, Any]], str],
    safe_str_func: Callable[..., str],
) -> dict[str, Any] | None:
    if not runtime._owner_private_payload_matches(payload):
        return None
    followup = compose_followup_func(runtime.xinyu_dir, text)
    if not followup:
        return None

    reply, guard_flags = guarded_followup_reply(
        runtime,
        payload,
        followup,
        text=text,
        safe_str_func=safe_str_func,
    )
    if not reply:
        return None

    row = followup_row(followup)
    notes = followup_status_notes(
        followup,
        row,
        intercept_note=spec.intercept_note,
        row_note_func=spec.row_note_func,
        event_sidecar=event_sidecar,
        cleanup=cleanup,
        guard_flags=guard_flags,
        safe_str_func=safe_str_func,
        extend_common_finish_notes_func=extend_common_finish_notes_func,
    )
    return await finish_followup_response(
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
        result_key=spec.result_key,
        result_payload=spec.result_payload_func(followup, row, safe_str_func),
        finish_action_turn_func=finish_action_turn_func,
        memory_snapshot_func=memory_snapshot_func,
        record_turn_finished_func=record_turn_finished_func,
        visible_text_hash_func=visible_text_hash_func,
        timestamp_or_now_iso_func=timestamp_or_now_iso_func,
        command_id_func=command_id_func,
    )
