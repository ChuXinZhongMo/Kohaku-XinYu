from __future__ import annotations

from collections.abc import Callable
from typing import Any

import xinyu_bridge_semantic_fast_routes
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_bridge_slow_live_reply_repairs import (
    apply_current_reference_repair as _apply_current_reference_repair,
)
from xinyu_bridge_slow_live_reply_repairs import (
    apply_stale_context_repair as _apply_stale_context_repair,
)
from xinyu_bridge_values import dedupe as _dedupe
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_current_reference_guard import repair_current_reference_reply


def _with_default(value: Any, fallback: Any) -> Any:
    return fallback if value is None else value


def apply_slow_live_stale_context_repair(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    user_text: str,
    final_guard_flags: list[str],
    blocked_by_delegate: bool,
    owner_private_match_func: Callable[..., bool],
    stale_reply_func: Callable[[str], bool] | None = None,
    repair_reply_func: Callable[..., str] | None = None,
    normalize_func: Callable[[str], str] | None = None,
    dedupe_func: Callable[[list[str]], list[str]] | None = None,
) -> dict[str, Any]:
    return _apply_stale_context_repair(
        runtime,
        session,
        payload,
        reply=reply,
        user_text=user_text,
        final_guard_flags=final_guard_flags,
        blocked_by_delegate=blocked_by_delegate,
        owner_private_match_func=owner_private_match_func,
        stale_reply_func=_with_default(
            stale_reply_func,
            xinyu_bridge_semantic_fast_routes.reply_looks_like_stale_plan_residue,
        ),
        repair_reply_func=_with_default(
            repair_reply_func,
            xinyu_bridge_semantic_fast_routes.owner_private_direct_repair_reply,
        ),
        normalize_func=_with_default(normalize_func, normalize_bridge_reply),
        dedupe_func=_with_default(dedupe_func, _dedupe),
    )


def apply_slow_live_current_reference_repair(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    user_text: str,
    final_guard_flags: list[str],
    blocked_by_delegate: bool,
    owner_private_match_func: Callable[..., bool],
    repair_func: Callable[..., dict[str, Any]] | None = None,
    safe_str_func: Callable[..., str] | None = None,
    dedupe_func: Callable[[list[str]], list[str]] | None = None,
) -> dict[str, Any]:
    return _apply_current_reference_repair(
        runtime,
        session,
        payload,
        reply=reply,
        user_text=user_text,
        final_guard_flags=final_guard_flags,
        blocked_by_delegate=blocked_by_delegate,
        owner_private_match_func=owner_private_match_func,
        repair_func=_with_default(repair_func, repair_current_reference_reply),
        safe_str_func=_with_default(safe_str_func, _safe_str),
        dedupe_func=_with_default(dedupe_func, _dedupe),
    )
