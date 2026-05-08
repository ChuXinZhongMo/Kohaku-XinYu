from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

from xinyu_bridge_state_text import parse_iso
from xinyu_bridge_values import as_bool, dedupe, safe_str
from xinyu_bridge_desktop_actions import desktop_scrub_action_markers


def desktop_marker_count(items: list[Any], markers: tuple[str, ...]) -> int:
    lowered_markers = tuple(marker.lower() for marker in markers)
    count = 0
    for item in items:
        text = safe_str(item).lower()
        if any(marker in text for marker in lowered_markers):
            count += 1
    return count


def desktop_recall_count(result: Any) -> int:
    if result is None:
        return 0
    return len(list(getattr(result, "items", ()) or ()))


def desktop_top_recall_sources(result: Any) -> list[str]:
    if result is None:
        return []
    sources = [safe_str(getattr(item, "source", "")) for item in list(getattr(result, "items", ()) or ())]
    return dedupe([source for source in sources if source])[:6]


def desktop_proactive_expired(expires_at: str) -> bool:
    if expires_at in {"", "none", "unknown"}:
        return False
    parsed = parse_iso(expires_at)
    if parsed is None:
        return False
    return datetime.now().astimezone() >= parsed


def desktop_session_kind(payload: dict[str, Any]) -> str:
    message_type = safe_str(payload.get("message_type")).lower()
    platform = safe_str(payload.get("platform")).lower()
    if platform == "desktop" or message_type.startswith("desktop"):
        return "desktop_private"
    if message_type.startswith("group") or safe_str(payload.get("group_id")).strip():
        return "qq_group"
    if message_type.startswith("private") or safe_str(payload.get("user_id")).strip():
        return "qq_private"
    return "system"


def desktop_display_id(value: Any) -> str:
    text = safe_str(value).strip()
    if re.fullmatch(r"\d{4,20}", text):
        return text
    return ""


def desktop_avatar_url(
    payload: dict[str, Any],
    *,
    session_kind: str,
    user_display_id: str,
) -> str:
    if session_kind in {"qq_private", "qq_group"} and user_display_id:
        return f"https://q1.qlogo.cn/g?b=qq&nk={user_display_id}&s=100"
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        avatar = safe_str(metadata.get("avatar_url") or metadata.get("qq_avatar_url")).strip()
        if avatar.startswith(("http://", "https://")):
            return avatar
    return ""


def desktop_group_avatar_url(group_display_id: str) -> str:
    if group_display_id:
        return f"https://p.qlogo.cn/gh/{group_display_id}/{group_display_id}/100"
    return ""


def desktop_privacy_for_payload(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    message_type = safe_str(payload.get("message_type")).lower()
    source = safe_str(payload.get("source") or metadata.get("source")).lower()
    if message_type.startswith("group") or safe_str(payload.get("group_id")).strip():
        return "group_context"
    if message_type.startswith("system") or source.startswith("maintenance"):
        return "system_internal"
    if as_bool(metadata.get("is_owner_user"), default=False):
        return "owner_private"
    return "external_private"


def desktop_hash(value: Any, *, length: int = 16) -> str:
    text = safe_str(value).strip()
    if not text:
        return ""
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def desktop_text_preview(text: str, *, limit: int) -> str:
    compact = re.sub(r"\s+", " ", desktop_scrub_action_markers(text)).strip()
    if limit > 3 and len(compact) > limit:
        return compact[: limit - 3].rstrip() + "..."
    return compact
