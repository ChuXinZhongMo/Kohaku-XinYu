from __future__ import annotations

from collections.abc import Callable
from typing import Any


def apply_sticker_reply_override(
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    user_text: str,
    current_reply_func: Callable[..., Any],
    recent_reply_func: Callable[..., Any],
    replace_reply_func: Callable[..., Any],
) -> dict[str, Any]:
    current_sticker_reply = current_reply_func(user_text, payload)
    recent_sticker_reply = (
        "" if current_sticker_reply else recent_reply_func(user_text, session.dialogue_tail)
    )
    selected_reply = current_sticker_reply or recent_sticker_reply
    if selected_reply:
        reply = selected_reply
        replace_reply_func(session.agent, reply)
    return {
        "reply": reply,
        "current_sticker_reply": current_sticker_reply,
        "recent_sticker_reply": recent_sticker_reply,
    }
