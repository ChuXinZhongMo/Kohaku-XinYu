from __future__ import annotations

from xinyu_qq_bridge_errors import (
    BRIDGE_TIMEOUT_OWNER_REPLY,
    is_bridge_request_timeout_error,
    is_retryable_core_chat_connection_error,
    owner_private_chat_fallback_reply,
)


def test_bridge_timeout_error_accepts_timeout_markers() -> None:
    assert is_bridge_request_timeout_error('core bridge HTTP 504: {"notes": ["bridge_request_timeout"]}')
    assert is_bridge_request_timeout_error("core bridge request timed out after 10s")
    assert not is_bridge_request_timeout_error("core bridge HTTP 500: boom")


def test_retryable_core_chat_connection_error_requires_connection_marker() -> None:
    assert is_retryable_core_chat_connection_error(
        "core bridge connection failed: [WinError 10061] actively refused"
    )
    assert is_retryable_core_chat_connection_error("RemoteDisconnected: remote end closed")
    assert not is_retryable_core_chat_connection_error("core bridge HTTP 500: boom")


def test_owner_private_chat_fallback_reply_is_owner_private_only() -> None:
    assert (
        owner_private_chat_fallback_reply(
            route="chat",
            target_message_kind="private",
            target_user_id="42",
            owner_user_ids=frozenset({"42"}),
            reply_text=BRIDGE_TIMEOUT_OWNER_REPLY,
        )
        == BRIDGE_TIMEOUT_OWNER_REPLY
    )
    assert (
        owner_private_chat_fallback_reply(
            route="chat",
            target_message_kind="group",
            target_user_id="42",
            owner_user_ids=frozenset({"42"}),
            reply_text=BRIDGE_TIMEOUT_OWNER_REPLY,
        )
        == ""
    )
