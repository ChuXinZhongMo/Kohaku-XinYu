from __future__ import annotations

from typing import Any, Mapping


async def handle_recent_action_followup_turn_runtime(
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
    deps: Mapping[str, Any],
) -> dict[str, Any] | None:
    return await _handle_action_followup_turn(
        deps["_runtime_handle_recent_action_followup_turn"],
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
        compose_func=deps["compose_recent_action_followup"],
        compose_key="compose_recent_action_followup_func",
        deps=deps,
    )


async def handle_action_digest_followup_turn_runtime(
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
    deps: Mapping[str, Any],
) -> dict[str, Any] | None:
    return await _handle_action_followup_turn(
        deps["_runtime_handle_action_digest_followup_turn"],
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
        compose_func=deps["compose_action_digest_followup"],
        compose_key="compose_action_digest_followup_func",
        deps=deps,
    )


async def _handle_action_followup_turn(
    handler: Any,
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
    compose_func: Any,
    compose_key: str,
    deps: Mapping[str, Any],
) -> dict[str, Any] | None:
    return await handler(
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
        **{compose_key: compose_func},
        memory_snapshot_func=deps["_memory_snapshot"],
        record_turn_finished_func=deps["record_turn_finished"],
        visible_text_hash_func=deps["visible_text_hash"],
        timestamp_or_now_iso_func=deps["_timestamp_or_now_iso"],
        command_id_func=deps["_command_id"],
        safe_str_func=deps["_safe_str"],
    )
