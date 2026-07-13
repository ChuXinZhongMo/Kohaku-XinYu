from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_desktop_snapshot_memory import (
    desktop_latest_memory_route,
    desktop_memory_route_payload,
    desktop_recall_item,
)
from xinyu_bridge_desktop_snapshot_metrics import (
    desktop_creative_writing_state,
    desktop_initiative_metrics_summary,
    desktop_metric_int,
)


def desktop_turn_base(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session_key: str,
    turn_id: str,
    safe_str_func: Callable[..., str],
    as_bool_func: Callable[..., bool],
) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    source = safe_str_func(payload.get("source") or payload.get("adapter") or "qq_gateway", "qq_gateway")
    session_kind = runtime._desktop_session_kind(payload)
    user_display_id = runtime._desktop_display_id(payload.get("user_id"))
    group_display_id = runtime._desktop_display_id(payload.get("group_id"))
    return {
        "turnId": safe_str_func(turn_id),
        "commandId": safe_str_func(metadata.get("desktop_command_id") or payload.get("command_id")),
        "sessionHash": runtime._desktop_hash(session_key),
        "sessionKind": session_kind,
        "sessionLabel": runtime._desktop_session_label(payload, session_kind=session_kind, metadata=metadata),
        "accountLabel": runtime._desktop_account_label(
            payload,
            session_kind=session_kind,
            metadata=metadata,
            user_display_id=user_display_id,
            group_display_id=group_display_id,
        ),
        "avatarUrl": runtime._desktop_avatar_url(
            payload,
            session_kind=session_kind,
            user_display_id=user_display_id,
        ),
        "groupAvatarUrl": runtime._desktop_group_avatar_url(group_display_id),
        "platform": safe_str_func(payload.get("platform"), "qq"),
        "source": source,
        "messageType": safe_str_func(payload.get("message_type")),
        "isOwner": as_bool_func(metadata.get("is_owner_user"), default=False),
        "isTrusted": as_bool_func(metadata.get("is_trusted_user"), default=False),
        "trustLevel": safe_str_func(metadata.get("user_trust_level")),
        "senderName": runtime._desktop_text_preview(safe_str_func(payload.get("sender_name")), limit=80),
        "userDisplayId": user_display_id,
        "groupDisplayId": group_display_id,
        "userHash": runtime._desktop_hash(payload.get("user_id")),
        "groupHash": runtime._desktop_hash(payload.get("group_id")),
        "messageHash": runtime._desktop_hash(payload.get("message_id")),
    }

__all__ = (
    "Any",
    "Callable",
    "annotations",
    "desktop_creative_writing_state",
    "desktop_initiative_metrics_summary",
    "desktop_latest_memory_route",
    "desktop_memory_route_payload",
    "desktop_metric_int",
    "desktop_recall_item",
    "desktop_turn_base",
)
