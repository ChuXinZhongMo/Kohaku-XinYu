from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_semantic_fast_finish_core_dedupe import dedupe_semantic_fast_visible_reply


def guard_semantic_fast_visible_reply(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    rendered_reply: str,
) -> tuple[str, Any] | None:
    guarded_reply, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=text,
        reply=rendered_reply,
    )
    if not guarded_reply:
        return None
    return guarded_reply, guard_flags


def prepare_semantic_fast_visible_reply(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    rendered_reply: str,
    normalize_reply_func: Callable[[str], str],
    dedupe_visible_reply_func: Callable[[str], Any],
) -> tuple[str, Any, Any] | None:
    guarded = guard_semantic_fast_visible_reply(
        runtime,
        payload,
        text=text,
        rendered_reply=rendered_reply,
    )
    if guarded is None:
        return None

    guarded_reply, guard_flags = guarded
    deduped = dedupe_semantic_fast_visible_reply(
        guarded_reply,
        normalize_reply_func=normalize_reply_func,
        dedupe_visible_reply_func=dedupe_visible_reply_func,
    )
    if deduped is None:
        return None

    reply, visible_dedupe = deduped
    return reply, guard_flags, visible_dedupe


__all__ = ["guard_semantic_fast_visible_reply", "prepare_semantic_fast_visible_reply"]
