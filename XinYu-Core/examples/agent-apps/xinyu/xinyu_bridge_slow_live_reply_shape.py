from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_human_voice_flags import regen_pipeline_enabled
from xinyu_reply_source import FinalTextSource, note_for_final_text_source


FALSE_SINGLE_BUBBLE_REPLY = "可以拆。你要我拆哪段，我按一条一条发。"
STYLE_PRESSURE_EMPTY_REPLY = "哪句最明显？"


def apply_reply_bubble_policy(
    runtime: Any,
    session: Any,
    *,
    reply: str,
    user_text: str,
    dialogue_tail: list[dict[str, Any]],
    final_guard_flags: list[str],
    false_single_bubble_reply: str = FALSE_SINGLE_BUBBLE_REPLY,
    dedupe_func: Callable[[list[str]], list[str]],
) -> dict[str, Any]:
    reply_bubble_force_units = runtime._owner_requested_reply_bubble_units(
        user_text=user_text,
        reply=reply,
        dialogue_tail=dialogue_tail,
    )
    if reply_bubble_force_units:
        reply = " ".join(reply_bubble_force_units)
        final_guard_flags = dedupe_func(list(final_guard_flags or []) + ["owner_explicit_reply_bubble_units"])
        runtime._replace_last_assistant_message(session.agent, reply)
    elif runtime._looks_like_false_single_bubble_limitation(user_text, reply):
        if regen_pipeline_enabled():
            # plan §5 阶段4: clear instead of substituting the canned line; the
            # already-async, model-first empty-recovery step regenerates it, with
            # the canned constant remaining as last-resort insurance.
            reply = ""
            final_guard_flags = dedupe_func(
                list(final_guard_flags or [])
                + ["false_single_message_limit_naturalized", "false_single_bubble_regen_pending"]
            )
        else:
            reply = false_single_bubble_reply
            final_guard_flags = dedupe_func(list(final_guard_flags or []) + ["false_single_message_limit_naturalized"])
            runtime._replace_last_assistant_message(session.agent, reply)
    return {
        "reply": reply,
        "final_guard_flags": final_guard_flags,
        "reply_bubble_force_units": reply_bubble_force_units,
    }


def apply_style_pressure_empty_fallback(
    runtime: Any,
    session: Any,
    *,
    reply: str,
    final_guard_flags: list[str],
    style_pressure_empty_reply: str = STYLE_PRESSURE_EMPTY_REPLY,
    dedupe_func: Callable[[list[str]], list[str]],
) -> dict[str, Any]:
    if not reply and "style_pressure_template_blocked" in final_guard_flags:
        if regen_pipeline_enabled():
            # Leave the reply empty so the model-first empty-recovery step
            # regenerates a real line instead of the "哪句最明显？" constant.
            final_guard_flags = dedupe_func(list(final_guard_flags or []) + ["style_pressure_empty_regen_pending"])
        else:
            reply = style_pressure_empty_reply
            final_guard_flags = dedupe_func(list(final_guard_flags or []) + ["style_pressure_empty_reply_fallback"])
            runtime._replace_last_assistant_message(session.agent, reply)
    return {"reply": reply, "final_guard_flags": final_guard_flags}


async def recover_empty_visible_reply(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    user_text: str,
    final_guard_flags: list[str],
    rendered: bool,
    renderer_reason: str,
    recalled_context: Any,
    blocked_by_delegate: bool,
    owner_private_match_func: Callable[..., bool],
    safe_str_func: Callable[..., str],
    dedupe_func: Callable[[list[str]], list[str]],
) -> dict[str, Any]:
    if not reply and owner_private_match_func(runtime, payload) and not blocked_by_delegate:
        recovered_reply, recovery_flags = await runtime._recover_empty_visible_reply(
            session.agent,
            payload=payload,
            user_text=user_text,
            canonical_recall_context=safe_str_func(getattr(recalled_context, "prompt_block", "")),
        )
        if recovery_flags:
            final_guard_flags = dedupe_func(list(final_guard_flags or []) + list(recovery_flags))
        if recovered_reply:
            reply = recovered_reply
            rendered = True
            renderer_reason = renderer_reason or "empty_visible_reply_retry"
            if regen_pipeline_enabled():
                final_guard_flags = dedupe_func(
                    list(final_guard_flags or []) + [note_for_final_text_source(FinalTextSource.MODEL_REGEN)]
                )
            runtime._replace_last_assistant_message(session.agent, reply)

    if not reply:
        fallback_reply = runtime._empty_visible_reply_fallback(payload=payload, user_text=user_text)
        if fallback_reply:
            reply = fallback_reply
            extra_flags = ["empty_visible_reply_fallback"]
            if regen_pipeline_enabled():
                extra_flags.append(note_for_final_text_source(FinalTextSource.CANNED_EMPTY_STATE))
            final_guard_flags = dedupe_func(list(final_guard_flags or []) + extra_flags)
            runtime._replace_last_assistant_message(session.agent, reply)

    empty_visible_reply_no_fallback = bool(not reply and owner_private_match_func(runtime, payload))
    return {
        "reply": reply,
        "final_guard_flags": final_guard_flags,
        "rendered": rendered,
        "renderer_reason": renderer_reason,
        "empty_visible_reply_no_fallback": empty_visible_reply_no_fallback,
    }
