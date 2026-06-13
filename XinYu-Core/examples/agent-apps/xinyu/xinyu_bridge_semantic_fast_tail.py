from __future__ import annotations

from typing import Any


def update_semantic_fast_session_tail(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    reply: str,
    session: Any | None,
) -> None:
    if session is None:
        return
    try:
        runtime._replace_last_assistant_message(session.agent, reply)
    except Exception:
        pass
    try:
        runtime._append_dialogue_tail(session, user_text=text, reply=reply, payload=payload)
    except Exception as exc:
        print(f"[xinyu_core_bridge] semantic fast dialogue tail failed: {type(exc).__name__}: {exc}", flush=True)
