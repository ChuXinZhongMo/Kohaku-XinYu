from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_visible_reply_guard import dedupe_visible_reply


def apply_slow_live_visible_dedupe(
    runtime: Any,
    session: Any,
    reply: str,
    *,
    dedupe_func: Callable[..., Any] = dedupe_visible_reply,
) -> dict[str, Any]:
    visible_dedupe = dedupe_func(reply)
    if visible_dedupe.changed:
        reply = visible_dedupe.text
        runtime._replace_last_assistant_message(session.agent, reply)
    return {"reply": reply, "visible_dedupe": visible_dedupe}
