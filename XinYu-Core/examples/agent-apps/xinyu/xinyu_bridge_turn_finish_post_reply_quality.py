from __future__ import annotations

from typing import Any


def reply_quality_flags(runtime: Any, *, payload: dict[str, Any], text: str, reply: str) -> list[Any]:
    if not reply:
        return []
    return runtime.speech_controller.reply_quality_flags(payload=payload, user_text=text, reply=reply)
