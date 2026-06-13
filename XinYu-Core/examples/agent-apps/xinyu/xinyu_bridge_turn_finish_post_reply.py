from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_turn_finish_post_reply_shapes import (
    error_notes,
    expression_learning_notes_with_quality,
    is_owner_user_payload,
    learning_closed_loop_expression_notes,
    post_reply_observation_error,
    recalled_context_prompt_block,
    uncertainty_pause_reason,
    visible_turn_kind,
)
from xinyu_bridge_turn_finish_post_reply_quality import reply_quality_flags as _reply_quality_flags


def record_uncertainty_pause_sidecar(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    draft_reply: str,
    reply: str,
    final_guard_flags: list[str],
    session_key: str,
    visible_turn: Any,
    is_waiting_reply_func: Callable[[str], bool],
    record_uncertainty_pause_func: Callable[..., dict[str, Any]],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    reason = uncertainty_pause_reason(reply, final_guard_flags, is_waiting_reply_func)
    if not reason:
        return {"notes": []}
    try:
        return record_uncertainty_pause_func(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            draft_reply=draft_reply,
            final_reply=reply,
            reason=reason,
            final_guard_flags=final_guard_flags,
            session_key=session_key,
            visible_turn_kind=visible_turn_kind(visible_turn, safe_str_func),
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] uncertainty pause failed: {exc}", flush=True)
        return error_notes("uncertainty_pause_error", exc)


def observe_post_reply_self_observation_sidecar(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    visible_turn: Any,
    final_guard_flags: list[str],
    expression_learning: dict[str, Any],
    recalled_context: Any,
    observe_post_reply_self_observation_func: Callable[..., dict[str, Any]],
    dedupe_func: Callable[..., list[Any]],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    try:
        quality_flags = _reply_quality_flags(runtime, payload=payload, text=text, reply=reply)
        expression_learning["notes"] = expression_learning_notes_with_quality(
            expression_learning,
            quality_flags,
            safe_str_func=safe_str_func,
            dedupe_func=dedupe_func,
        )
        return observe_post_reply_self_observation_func(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            reply=reply,
            visible_turn=visible_turn,
            final_guard_flags=final_guard_flags,
            quality_flags=quality_flags,
            recalled_context=recalled_context_prompt_block(recalled_context, safe_str_func),
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] post-reply self observation failed: {exc}", flush=True)
        return post_reply_observation_error(exc)


def record_learning_closed_loop_sidecar(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    session_key: str,
    visible_turn: Any,
    final_guard_flags: list[str],
    expression_learning: dict[str, Any],
    post_reply_observation: dict[str, Any] | None,
    record_learning_closed_loop_turn_func: Callable[..., dict[str, Any]],
    dedupe_func: Callable[..., list[Any]],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    try:
        quality_flags = _reply_quality_flags(runtime, payload=payload, text=text, reply=reply)
        expression_notes = learning_closed_loop_expression_notes(
            expression_learning,
            post_reply_observation,
            safe_str_func=safe_str_func,
            dedupe_func=dedupe_func,
        )
        return record_learning_closed_loop_turn_func(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            reply=reply,
            session_key=session_key,
            visible_turn_kind=visible_turn_kind(visible_turn, safe_str_func),
            final_guard_flags=final_guard_flags,
            quality_flags=quality_flags,
            expression_notes=expression_notes,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] learning closed loop failed: {exc}", flush=True)
        return error_notes("learning_closed_loop_error", exc)


def record_owner_voice_sidecars(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    as_bool_func: Callable[..., bool],
    record_voice_trial_overlay_func: Callable[..., dict[str, Any]],
    record_voice_correction_func: Callable[..., bool],
) -> tuple[dict[str, Any], bool]:
    if not is_owner_user_payload(payload, as_bool_func):
        return {"notes": []}, False
    try:
        overlay = record_voice_trial_overlay_func(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            reply=reply,
            source="qq_gateway",
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] voice trial overlay failed: {exc}", flush=True)
        overlay = error_notes("voice_trial_overlay_error", exc)
    calibrated = record_voice_correction_func(runtime.xinyu_dir, user_text=text, reply=reply, source="qq_gateway")
    return overlay, calibrated


def record_curiosity_prediction_sidecar(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    session_key: str,
    record_reply_prediction_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    try:
        return record_reply_prediction_func(runtime.xinyu_dir, payload, user_text=text, reply=reply, session_key=session_key)
    except Exception as exc:
        print(f"[xinyu_core_bridge] dialogue curiosity prediction failed: {exc}", flush=True)
        return error_notes("dialogue_curiosity_prediction_error", exc)


def record_private_thought_link_sidecar(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    session_key: str,
    record_private_thought_reply_link_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    try:
        return record_private_thought_reply_link_func(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            reply=reply,
            session_key=session_key,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] private thought reply link failed: {exc}", flush=True)
        return error_notes("private_thought_link_error", exc)
