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
        safe_str_func=safe_str_func,
    )
