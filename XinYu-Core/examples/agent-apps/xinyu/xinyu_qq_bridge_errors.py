from __future__ import annotations

BRIDGE_TIMEOUT_OWNER_REPLY = (
    "\u6211\u8fd9\u8fb9\u5361\u4f4f\u4e86\uff0c\u521a\u624d\u90a3\u53e5\u6536\u5230\uff0c"
    "\u4f46\u6838\u5fc3\u56de\u590d\u8d85\u65f6\u3002\u7b49\u6211\u6062\u590d\u518d\u63a5\u3002"
)
BRIDGE_UNAVAILABLE_OWNER_REPLY = (
    "\u6211\u6536\u5230\u4e86\uff0c\u4f46\u521a\u624d\u8fd9\u8fb9\u91cd\u542f\u65ad\u5f00\u4e86\uff0c"
    "\u90a3\u6761\u6ca1\u8dd1\u5b8c\u3002\u4f60\u518d\u53d1\u4e00\u6b21\uff0c\u6211\u73b0\u5728\u63a5\u3002"
)


def is_bridge_request_timeout_error(error: str) -> bool:
    lowered = error.lower()
    return (
        "bridge_request_timeout" in lowered
        or "core bridge request timed out" in lowered
        or "core bridge connection failed: timed out" in lowered
    )


def is_retryable_core_chat_connection_error(error: str) -> bool:
    lowered = error.lower()
    if "core bridge connection failed" not in lowered and "remotedisconnected" not in lowered:
        return False
    return any(
        marker in lowered
        for marker in (
            "winerror 10053",
            "winerror 10054",
            "winerror 10061",
            "connection reset",
            "connection aborted",
            "connection refused",
            "forcibly closed",
            "remote end closed",
            "remote disconnected",
            "remotedisconnected",
            "actively refused",
        )
    )


def is_bridge_connection_unavailable_error(error: str) -> bool:
    return is_retryable_core_chat_connection_error(error)


def owner_private_chat_fallback_reply(
    *,
    route: str,
    target_message_kind: str,
    target_user_id: str,
    owner_user_ids: set[str] | frozenset[str],
    reply_text: str,
) -> str:
    if route != "chat":
        return ""
    if target_message_kind != "private":
        return ""
    if target_user_id not in owner_user_ids:
        return ""
    return reply_text
