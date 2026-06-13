from __future__ import annotations

from typing import Any, Callable, NamedTuple


class PostReplyFinishResult(NamedTuple):
    uncertainty_pause: dict[str, Any]
    post_reply_observation: dict[str, Any]
    learning_closed_loop: dict[str, Any]
    residue_written: bool
    voice_calibrated: bool
    voice_trial_overlay: dict[str, Any]
    curiosity_prediction: dict[str, Any]
    private_thought_link: dict[str, Any]


def run_post_reply_finish_sidecars(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    draft_reply: str,
    session_key: str,
    visible_turn: Any,
    final_guard_flags: list[str],
    expression_learning: dict[str, Any],
    recalled_context: Any,
    record_uncertainty_pause_func: Callable[..., dict[str, Any]],
    observe_post_reply_self_observation_func: Callable[..., dict[str, Any]],
    record_learning_closed_loop_func: Callable[..., dict[str, Any]],
    write_turn_residue_func: Callable[..., bool],
    record_owner_voice_sidecars_func: Callable[..., tuple[dict[str, Any], bool]],
    record_curiosity_prediction_func: Callable[..., dict[str, Any]],
    record_private_thought_link_func: Callable[..., dict[str, Any]],
) -> PostReplyFinishResult:
    uncertainty_pause = record_uncertainty_pause_func(
        runtime,
        payload=payload,
        text=text,
        draft_reply=draft_reply,
        reply=reply,
        final_guard_flags=final_guard_flags,
        session_key=session_key,
        visible_turn=visible_turn,
    )
    post_reply_observation = observe_post_reply_self_observation_func(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        visible_turn=visible_turn,
        final_guard_flags=final_guard_flags,
        expression_learning=expression_learning,
        recalled_context=recalled_context,
    )
    learning_closed_loop = record_learning_closed_loop_func(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session_key=session_key,
        visible_turn=visible_turn,
        final_guard_flags=final_guard_flags,
        expression_learning=expression_learning,
        post_reply_observation=post_reply_observation,
    )
    residue_written = write_turn_residue_func(
        runtime.xinyu_dir,
        scene=runtime.speech_controller.classify(payload=payload, user_text=text),
        user_text=text,
        reply=reply,
        source="qq_gateway",
    )
    voice_trial_overlay, voice_calibrated = record_owner_voice_sidecars_func(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
    )
    curiosity_prediction = record_curiosity_prediction_func(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session_key=session_key,
    )
    private_thought_link = record_private_thought_link_func(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session_key=session_key,
    )
    return PostReplyFinishResult(
        uncertainty_pause=uncertainty_pause,
        post_reply_observation=post_reply_observation,
        learning_closed_loop=learning_closed_loop,
        residue_written=residue_written,
        voice_calibrated=voice_calibrated,
        voice_trial_overlay=voice_trial_overlay,
        curiosity_prediction=curiosity_prediction,
        private_thought_link=private_thought_link,
    )
