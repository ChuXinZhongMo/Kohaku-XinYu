from __future__ import annotations

from typing import Any, Mapping

from xinyu_bridge_action_route_runtime_followups import (
    handle_action_digest_followup_turn_runtime,
    handle_recent_action_followup_turn_runtime,
)

__all__ = (
    "handle_action_digest_followup_turn_runtime",
    "handle_action_layer_turn_runtime",
    "handle_recent_action_followup_turn_runtime",
    "settle_action_experience_runtime",
)



async def settle_action_experience_runtime(
    runtime: Any,
    payload: dict[str, Any],
    *,
    request: dict[str, Any],
    outcome: dict[str, Any],
    deps: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    return await deps["_runtime_settle_action_experience"](
        runtime,
        payload,
        request=request,
        outcome=outcome,
        build_experience_frame_func=deps["build_experience_frame"],
        record_action_experience_event_func=deps["record_action_experience_event"],
        write_action_experience_residue_func=deps["write_action_experience_residue"],
        digest_action_experience_residue_func=deps["digest_action_experience_residue"],
        write_recent_action_experience_func=deps["write_recent_action_experience"],
        sanitize_visible_state_files_func=deps["sanitize_visible_state_files"],
        safe_str_func=deps["_safe_str"],
    )


async def handle_action_layer_turn_runtime(
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
    bridge_request_error_type: type[BaseException] | None,
    deps: Mapping[str, Any],
) -> dict[str, Any] | None:
    return await deps["_runtime_handle_action_layer_turn"](
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
        bridge_request_error_type=bridge_request_error_type,
        execute_action_request_func=deps["_runtime_execute_action_request"],
        settle_action_experience_func=deps["settle_action_experience"],
        compose_action_reply_func=deps["compose_action_reply"],
        safe_str_func=deps["_safe_str"],
        to_thread_func=deps["asyncio"].to_thread,
        codex_response_to_outcome_func=deps["codex_response_to_outcome"],
        external_response_to_outcome_func=deps["external_response_to_outcome"],
        looks_like_owner_local_write_request_func=deps["looks_like_owner_local_write_request"],
        action_outcome_cls=deps["ActionOutcome"],
        delegated_local_risk=deps["DELEGATED_LOCAL_RISK"],
    )

