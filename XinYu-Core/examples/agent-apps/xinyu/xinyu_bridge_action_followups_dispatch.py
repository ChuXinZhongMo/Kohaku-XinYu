from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_action_followup_core import ActionFollowupSpec
from xinyu_bridge_action_followups_deps import ActionFollowupFacadeDeps


async def dispatch_action_followup_turn(
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
    facade_deps: ActionFollowupFacadeDeps,
    memory_snapshot_func: Callable[[Any], dict[str, Any]],
    record_turn_finished_func: Callable[..., Any],
    visible_text_hash_func: Callable[[str], str],
    timestamp_or_now_iso_func: Callable[[Any], str],
    command_id_func: Callable[[dict[str, Any]], str],
    safe_str_func: Callable[..., str],
) -> dict[str, Any] | None:
    return await facade_deps.handle_action_followup_turn_impl(
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
        spec=spec,
        finish_action_turn_func=facade_deps.finish_action_turn,
        extend_common_finish_notes_func=facade_deps.extend_common_finish_notes,
        memory_snapshot_func=memory_snapshot_func,
        record_turn_finished_func=record_turn_finished_func,
        visible_text_hash_func=visible_text_hash_func,
        timestamp_or_now_iso_func=timestamp_or_now_iso_func,
        command_id_func=command_id_func,
        safe_str_func=safe_str_func,
    )
