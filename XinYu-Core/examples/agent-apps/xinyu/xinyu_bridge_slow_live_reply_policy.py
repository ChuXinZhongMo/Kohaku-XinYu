from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_values import safe_str as _safe_str
from xinyu_life_reply_policy import apply_life_reply_policy


def apply_slow_live_life_reply_policy(
    runtime: Any,
    session: Any,
    *,
    reply: str,
    user_text: str,
    life_reply_policy: dict[str, Any],
    blocked_by_delegate: bool,
    policy_func: Callable[..., dict[str, Any]] = apply_life_reply_policy,
    safe_str_func: Callable[..., str] = _safe_str,
) -> dict[str, Any]:
    life_reply_adjustment: dict[str, Any] = {"notes": []}
    if blocked_by_delegate:
        return {"reply": reply, "life_reply_adjustment": life_reply_adjustment}

    life_reply_adjustment = policy_func(reply, policy=life_reply_policy, user_text=user_text)
    if life_reply_adjustment.get("changed"):
        reply = safe_str_func(life_reply_adjustment.get("reply")).strip()
        runtime._replace_last_assistant_message(session.agent, reply)
    return {"reply": reply, "life_reply_adjustment": life_reply_adjustment}
