from __future__ import annotations

from typing import Any

from xinyu_bridge_codex_policy_markers import (
    OWNER_DIRECT_CODEX_DELEGATE_MARKERS,
    OWNER_DIRECT_CODEX_NEGATIVE_MARKERS,
    OWNER_DIRECT_CODEX_SUPPORT_MARKERS,
)
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_codex_delegate import looks_like_codex_request


def owner_direct_codex_task(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    session_key: str,
    delegate_markers: tuple[str, ...] = OWNER_DIRECT_CODEX_DELEGATE_MARKERS,
    support_markers: tuple[str, ...] = OWNER_DIRECT_CODEX_SUPPORT_MARKERS,
    negative_markers: tuple[str, ...] = OWNER_DIRECT_CODEX_NEGATIVE_MARKERS,
) -> str:
    if not runtime._can_model_delegate_codex(payload):
        return ""
    compact_user = runtime._compact_promise_text(user_text)
    if any(marker in compact_user for marker in negative_markers):
        return ""
    if not looks_like_codex_request(user_text):
        return ""
    has_direct_codex = any(marker in compact_user for marker in delegate_markers)
    has_support_context = any(marker in compact_user for marker in support_markers)
    if not (has_direct_codex or ("codex" in compact_user and has_support_context)):
        return ""
    compact_reply = runtime._compact_promise_text(reply)
    if "要现在开始吗" in compact_reply or "要现在开始" in compact_reply:
        pass
    elif any(marker in compact_reply for marker in ("开了", "让codex", "交给codex", "xinyucodex", "codex在新窗口")):
        return ""
    return normalize_bridge_reply(
        "\n".join(
            [
                "Owner explicitly asked XinYu to use Codex instead of stalling or asking for more permission.",
                f"Owner message: {user_text}",
                f"XinYu draft that failed to act: {reply}",
                f"Session: {session_key}",
                (
                    "Task: use web/repository research to find concrete ways to reduce XinYu's mechanical voice "
                    "and shallow context continuity, then report actionable project changes. Do not change files; "
                    "produce a concise report with sources or code pointers."
                ),
            ]
        )
    )


__all__ = ("owner_direct_codex_task",)
