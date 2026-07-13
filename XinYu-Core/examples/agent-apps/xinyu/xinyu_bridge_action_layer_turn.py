from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_action_finish import finish_action_turn
from xinyu_bridge_action_support import extend_common_finish_notes


async def handle_action_layer_turn(
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
    execute_action_request_func: Callable[..., Any],
    settle_action_experience_func: Callable[..., Any],
    compose_action_reply_func: Callable[..., str],
    safe_str_func: Callable[..., str],
    to_thread_func: Callable[..., Any],
    codex_response_to_outcome_func: Callable[..., dict[str, Any]],
    external_response_to_outcome_func: Callable[..., dict[str, Any]],
    looks_like_owner_local_write_request_func: Callable[[str], bool],
    action_outcome_cls: Any,
    delegated_local_risk: str,
) -> dict[str, Any] | None:
    decision = runtime.action_layer.route(payload, text, turn_id=turn_id)
    if decision.kind != "action_request" or decision.request is None:
        return None

    request = decision.request
    request_dict = request.to_dict()
    outcome = await execute_action_request_func(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        request=request,
        request_dict=request_dict,
        bridge_request_error_type=bridge_request_error_type,
        codex_response_to_outcome_func=codex_response_to_outcome_func,
        external_response_to_outcome_func=external_response_to_outcome_func,
        looks_like_owner_local_write_request_func=looks_like_owner_local_write_request_func,
        action_outcome_cls=action_outcome_cls,
        delegated_local_risk=delegated_local_risk,
        safe_str_func=safe_str_func,
        to_thread_func=to_thread_func,
    )
    frame, self_choice_public, experience_notes = await settle_action_experience_func(
        runtime,
        payload,
        request=request_dict,
        outcome=outcome,
    )
    reply = compose_action_reply_func(outcome, frame=frame, self_choice_public=self_choice_public)
    guarded_reply, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=text,
        reply=reply,
    )
    if guarded_reply:
        reply = guarded_reply

    notes = _action_layer_notes(
        decision=decision,
        request=request,
        outcome=outcome,
        experience_notes=experience_notes,
        event_sidecar=event_sidecar,
        cleanup=cleanup,
        guard_flags=guard_flags,
        safe_str_func=safe_str_func,
    )
    record_status = "ok" if outcome.get("ok") or outcome.get("result") == "blocked_by_boundary" else "error"
    return await finish_action_turn(
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
        record_status=record_status,
        extra_response={
            "action_outcome": outcome,
            "experience_frame": frame,
        },
    )


def _action_layer_notes(
    *,
    decision: Any,
    request: Any,
    outcome: dict[str, Any],
    experience_notes: list[str],
    event_sidecar: dict[str, Any],
    cleanup: dict[str, Any],
    guard_flags: list[str] | tuple[str, ...],
    safe_str_func: Callable[..., str],
) -> list[str]:
    notes: list[str] = [
        "action_layer_intercepted",
        f"action_layer_tool:{request.tool}",
    ]
    notes.extend(decision.notes[:4])
    notes.extend(safe_str_func(note) for note in outcome.get("notes", [])[:5])
    notes.extend(experience_notes[:8])
    extend_common_finish_notes(
        notes,
        event_sidecar=event_sidecar,
        cleanup=cleanup,
        guard_flags=guard_flags,
        safe_str_func=safe_str_func,
    )
    return notes
