from __future__ import annotations

from typing import Any

from xinyu_bridge_slow_live_reply_sticker import apply_sticker_reply_override as _apply_sticker_reply_override


def apply_slow_live_sticker_reply_override(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    user_text: str,
) -> dict[str, Any]:
    return _apply_sticker_reply_override(
        session,
        payload,
        reply=reply,
        user_text=user_text,
        current_reply_func=runtime._current_sticker_question_reply,
        recent_reply_func=runtime._recent_sticker_question_reply,
        replace_reply_func=runtime._replace_last_assistant_message,
    )
