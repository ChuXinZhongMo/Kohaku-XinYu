from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_slow_live_reply_shape import FALSE_SINGLE_BUBBLE_REPLY
from xinyu_bridge_slow_live_reply_shape import STYLE_PRESSURE_EMPTY_REPLY
from xinyu_bridge_slow_live_reply_shape import apply_reply_bubble_policy as _apply_reply_bubble_policy
from xinyu_bridge_slow_live_reply_shape import (
    apply_style_pressure_empty_fallback as _apply_style_pressure_empty_fallback,
)
from xinyu_bridge_slow_live_reply_shape import recover_empty_visible_reply as _recover_empty_visible_reply
from xinyu_bridge_values import dedupe as _dedupe
from xinyu_bridge_values import safe_str as _safe_str


def apply_slow_live_reply_bubble_policy(
    runtime: Any,
    session: Any,
    *,
    reply: str,
    user_text: str,
    dialogue_tail: list[dict[str, Any]],
    final_guard_flags: list[str],
    false_single_bubble_reply: str = FALSE_SINGLE_BUBBLE_REPLY,
    dedupe_func: Callable[[list[str]], list[str]] = _dedupe,
) -> dict[str, Any]:
    return _apply_reply_bubble_policy(
        runtime,
        session,
        reply=reply,
        user_text=user_text,
        dialogue_tail=dialogue_tail,
        final_guard_flags=final_guard_flags,
        false_single_bubble_reply=false_single_bubble_reply,
        dedupe_func=dedupe_func,
    )


def apply_slow_live_style_pressure_empty_fallback(
    runtime: Any,
    session: Any,
    *,
    reply: str,
    final_guard_flags: list[str],
    style_pressure_empty_reply: str = STYLE_PRESSURE_EMPTY_REPLY,
    dedupe_func: Callable[[list[str]], list[str]] = _dedupe,
) -> dict[str, Any]:
    return _apply_style_pressure_empty_fallback(
        runtime,
        session,
        reply=reply,
        final_guard_flags=final_guard_flags,
        style_pressure_empty_reply=style_pressure_empty_reply,
        dedupe_func=dedupe_func,
    )


async def recover_slow_live_empty_visible_reply(
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
    safe_str_func: Callable[..., str] = _safe_str,
    dedupe_func: Callable[[list[str]], list[str]] = _dedupe,
) -> dict[str, Any]:
    return await _recover_empty_visible_reply(
        runtime,
        session,
        payload,
        reply=reply,
        user_text=user_text,
        final_guard_flags=final_guard_flags,
        rendered=rendered,
        renderer_reason=renderer_reason,
        recalled_context=recalled_context,
        blocked_by_delegate=blocked_by_delegate,
        owner_private_match_func=owner_private_match_func,
        safe_str_func=safe_str_func,
        dedupe_func=dedupe_func,
    )
