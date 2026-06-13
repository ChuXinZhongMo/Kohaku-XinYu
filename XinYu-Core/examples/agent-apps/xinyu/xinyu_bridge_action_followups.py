from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_action_finish import finish_action_turn
from xinyu_bridge_action_followup_core import (
    ActionFollowupSpec,
    handle_action_followup_turn as _handle_action_followup_turn_impl,
)
from xinyu_bridge_action_followup_results import (
    action_digest_payload as _action_digest_payload,
    action_digest_row_note as _action_digest_row_note,
    recent_action_payload as _recent_action_payload,
    recent_action_row_note as _recent_action_row_note,
)
from xinyu_bridge_action_followups_deps import (
    ActionFollowupFacadeDeps,
    facade_deps as _facade_deps,
)
from xinyu_bridge_action_followups_dispatch import (
    dispatch_action_followup_turn as _dispatch_action_followup_turn,
)
from xinyu_bridge_action_support import extend_common_finish_notes


def _deps() -> ActionFollowupFacadeDeps:
    return _facade_deps(globals())


async def _handle_action_followup_turn(
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
    intercept_note: str,
    row_note_func: Callable[[dict[str, Any], Callable[..., str]], str],
    result_key: str,
    result_payload_func: Callable[[dict[str, Any], dict[str, Any], Callable[..., str]], dict[str, str]],
    memory_snapshot_func: Callable[[Any], dict[str, Any]],
    record_turn_finished_func: Callable[..., Any],
    visible_text_hash_func: Callable[[str], str],
    timestamp_or_now_iso_func: Callable[[Any], str],
    command_id_func: Callable[[dict[str, Any]], str],
    safe_str_func: Callable[..., str],
) -> dict[str, Any] | None:
    return await _dispatch_action_followup_turn(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
        compose_followup_func=compose_followup_func,
        spec=ActionFollowupSpec(
            intercept_note=intercept_note,
            row_note_func=row_note_func,
            result_key=result_key,
            result_payload_func=result_payload_func,
        ),
        facade_deps=_deps(),
        memory_snapshot_func=memory_snapshot_func,
        record_turn_finished_func=record_turn_finished_func,
        visible_text_hash_func=visible_text_hash_func,
        timestamp_or_now_iso_func=timestamp_or_now_iso_func,
        command_id_func=command_id_func,
        safe_str_func=safe_str_func,
    )


async def handle_recent_action_followup_turn(
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
    compose_recent_action_followup_func: Callable[[Any, str], dict[str, Any] | None],
    memory_snapshot_func: Callable[[Any], dict[str, Any]],
    record_turn_finished_func: Callable[..., Any],
    visible_text_hash_func: Callable[[str], str],
    timestamp_or_now_iso_func: Callable[[Any], str],
    command_id_func: Callable[[dict[str, Any]], str],
    safe_str_func: Callable[..., str],
) -> dict[str, Any] | None:
    return await _handle_action_followup_turn(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
        compose_followup_func=compose_recent_action_followup_func,
        intercept_note="recent_action_followup_intercepted",
        row_note_func=_recent_action_row_note,
        result_key="recent_action_followup",
        result_payload_func=_recent_action_payload,
        memory_snapshot_func=memory_snapshot_func,
        record_turn_finished_func=record_turn_finished_func,
        visible_text_hash_func=visible_text_hash_func,
        timestamp_or_now_iso_func=timestamp_or_now_iso_func,
        command_id_func=command_id_func,
        safe_str_func=safe_str_func,
    )


async def handle_action_digest_followup_turn(
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
    compose_action_digest_followup_func: Callable[[Any, str], dict[str, Any] | None],
    memory_snapshot_func: Callable[[Any], dict[str, Any]],
    record_turn_finished_func: Callable[..., Any],
    visible_text_hash_func: Callable[[str], str],
    timestamp_or_now_iso_func: Callable[[Any], str],
    command_id_func: Callable[[dict[str, Any]], str],
    safe_str_func: Callable[..., str],
) -> dict[str, Any] | None:
    return await _handle_action_followup_turn(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
        compose_followup_func=compose_action_digest_followup_func,
        intercept_note="action_digest_followup_intercepted",
        row_note_func=_action_digest_row_note,
        result_key="action_digest_followup",
        result_payload_func=_action_digest_payload,
        memory_snapshot_func=memory_snapshot_func,
        record_turn_finished_func=record_turn_finished_func,
        visible_text_hash_func=visible_text_hash_func,
        timestamp_or_now_iso_func=timestamp_or_now_iso_func,
        command_id_func=command_id_func,
        safe_str_func=safe_str_func,
    )
