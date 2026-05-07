from __future__ import annotations

import re
from typing import Any, Iterable


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def compact_command_text(text: str) -> str:
    return re.sub(r"\s+", "", safe_str(text)).lower()


def marker_command_matches(text: str, markers: Iterable[str]) -> bool:
    compact = compact_command_text(text)
    return bool(compact) and any(compact_command_text(marker) in compact for marker in markers)


def effective_whitelist_user_ids(config: Any) -> set[str]:
    return set(config.whitelist_user_ids) | set(config.owner_user_ids) | set(config.trusted_user_ids)


def is_blocked_user_id(config: Any, user_id: str) -> bool:
    user_id = safe_str(user_id).strip()
    return bool(user_id and user_id not in config.owner_user_ids and user_id in config.blocked_user_ids)


def is_blocked_group_id(config: Any, group_id: str) -> bool:
    group_id = safe_str(group_id).strip()
    return bool(group_id and group_id in config.blocked_group_ids)


def is_trusted_user_id(config: Any, user_id: str) -> bool:
    user_id = safe_str(user_id).strip()
    if not user_id or user_id in config.owner_user_ids:
        return False
    return user_id in config.trusted_user_ids or user_id in config.whitelist_user_ids


def trust_level_for_user_id(config: Any, user_id: str) -> str:
    user_id = safe_str(user_id).strip()
    if user_id in config.owner_user_ids:
        return "owner"
    if is_trusted_user_id(config, user_id):
        return "trusted"
    return "external"


def trust_command_target(prepared: Any, *, owner_user_ids: Iterable[str]) -> tuple[str, str]:
    payload = prepared.payload if isinstance(getattr(prepared, "payload", None), dict) else {}
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    reply_context = metadata.get("qq_reply_context")
    if isinstance(reply_context, dict):
        user_id = safe_str(reply_context.get("user_id")).strip()
        if user_id:
            return user_id, safe_str(reply_context.get("sender_name")).strip()

    owners = set(owner_user_ids)
    text = safe_str(payload.get("text")).strip()
    for match in re.finditer(r"(?<!\d)(\d{5,12})(?!\d)", text):
        user_id = match.group(1)
        if user_id and user_id not in owners:
            return user_id, ""
    return "", ""


def group_shadow_group_allowed(config: Any, group_id: str) -> bool:
    group_id = safe_str(group_id).strip()
    allowed = set(config.group_shadow_allowed_group_ids)
    return bool(group_id and group_id in allowed)
