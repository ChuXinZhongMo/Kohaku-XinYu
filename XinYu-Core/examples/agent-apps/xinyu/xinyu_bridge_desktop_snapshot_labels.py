from __future__ import annotations

from typing import Any, Callable


def desktop_session_label(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session_kind: str,
    metadata: dict[str, Any],
    safe_str_func: Callable[..., str],
    as_bool_func: Callable[..., bool],
) -> str:
    safe_str = safe_str_func
    as_bool = as_bool_func
    sender_name = runtime._desktop_text_preview(safe_str(payload.get("sender_name")), limit=48)
    user_hash = runtime._desktop_hash(payload.get("user_id"), length=8)
    group_hash = runtime._desktop_hash(payload.get("group_id"), length=8)
    fallback_contact = sender_name or (f"#{user_hash}" if user_hash else "未知联系人")
    if session_kind == "desktop_private":
        return "桌面主人"
    if session_kind == "qq_group":
        target = sender_name or (f"群#{group_hash}" if group_hash else "未知群聊")
        return f"QQ群聊 / {target}"
    if session_kind == "qq_private":
        if as_bool(metadata.get("is_owner_user"), default=False):
            relation = "主人QQ"
        elif as_bool(metadata.get("is_trusted_user"), default=False):
            relation = "可信QQ"
        else:
            relation = "外部QQ"
        return f"{relation} / {fallback_contact}"
    return "系统窗口"


def desktop_account_label(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session_kind: str,
    metadata: dict[str, Any],
    user_display_id: str,
    group_display_id: str,
    safe_str_func: Callable[..., str],
    as_bool_func: Callable[..., bool],
) -> str:
    safe_str = safe_str_func
    as_bool = as_bool_func
    if session_kind == "desktop_private":
        return "桌面 owner"
    if session_kind == "qq_group":
        parts = []
        if group_display_id:
            parts.append(f"群 {group_display_id}")
        if user_display_id:
            parts.append(f"QQ {user_display_id}")
        return " / ".join(parts) or "QQ群聊"
    if session_kind == "qq_private":
        prefix = (
            "主人QQ"
            if as_bool(metadata.get("is_owner_user"), default=False)
            else ("可信QQ" if as_bool(metadata.get("is_trusted_user"), default=False) else "外部QQ")
        )
        return f"{prefix} {user_display_id}" if user_display_id else prefix
    return safe_str(payload.get("platform"), "system")
