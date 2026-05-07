"""QQ/OneBot-specific gateway helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


PRIVATE_MESSAGE_TYPES = {"friend", "private", "FriendMessage", "private_message"}
GROUP_MESSAGE_TYPES = {"group", "GroupMessage", "group_message"}


def is_group_payload(payload: Mapping[str, Any]) -> bool:
    message_type = str(payload.get("message_type") or "").strip()
    return bool(payload.get("group_id")) or message_type in GROUP_MESSAGE_TYPES or message_type.lower().startswith("group")


def is_private_payload(payload: Mapping[str, Any]) -> bool:
    message_type = str(payload.get("message_type") or "").strip()
    if is_group_payload(payload):
        return False
    return not message_type or message_type in PRIVATE_MESSAGE_TYPES or message_type.lower().startswith("private")


def build_qq_session_id(platform_id: str, user_id: str, *, message_type: str = "FriendMessage") -> str:
    platform = platform_id.strip()
    user = user_id.strip()
    if not platform or not user:
        return ""
    return f"{platform}:{message_type}:{user}"
