from __future__ import annotations

from collections.abc import Callable
from typing import Any


def dedupe_semantic_fast_visible_reply(
    guarded_reply: str,
    *,
    normalize_reply_func: Callable[[str], str],
    dedupe_visible_reply_func: Callable[[str], Any],
) -> tuple[str, Any] | None:
    visible_dedupe = dedupe_visible_reply_func(normalize_reply_func(guarded_reply))
    reply = visible_dedupe.text
    if not reply:
        return None
    return reply, visible_dedupe


__all__ = ["dedupe_semantic_fast_visible_reply"]
