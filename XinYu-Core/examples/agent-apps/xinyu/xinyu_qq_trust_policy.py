from __future__ import annotations

import re
from typing import Any, Iterable


TRUST_GRANT_TEXT_MARKERS = (
    "给个权限",
    "给权限",
    "加权限",
    "开权限",
    "给她权限",
    "给他权限",
    "信任这个人",
    "信任她",
    "信任他",
    "允许她搜",
    "允许他搜",
    "让她搜",
    "让他搜",
    "给她搜索权限",
    "给他搜索权限",
    "trusted user",
    "trust this user",
)
TRUST_REVOKE_TEXT_MARKERS = (
    "取消权限",
    "撤销权限",
    "别信任",
    "不信任这个人",
    "取消信任",
    "revoke trust",
)


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def compact_command_text(text: str) -> str:
    return re.sub(r"\s+", "", safe_str(text)).lower()


def marker_command_matches(text: str, markers: Iterable[str]) -> bool:
    compact = compact_command_text(text)
    return bool(compact) and any(compact_command_text(marker) in compact for marker in markers)


def is_trust_grant_command(text: str) -> bool:
    return marker_command_matches(text, TRUST_GRANT_TEXT_MARKERS)


def is_trust_revoke_command(text: str) -> bool:
    return marker_command_matches(text, TRUST_REVOKE_TEXT_MARKERS)


def effective_whitelist_user_ids(config: Any) -> set[str]:
    return set(config.whitelist_user_ids) | set(config.owner_user_ids) | set(config.trusted_user_ids)


def gateway_effective_whitelist_user_ids(gateway: Any) -> set[str]:
    return effective_whitelist_user_ids(gateway.config)


def is_blocked_user_id(config: Any, user_id: str) -> bool:
    user_id = safe_str(user_id).strip()
    return bool(user_id and user_id not in config.owner_user_ids and user_id in config.blocked_user_ids)


def gateway_is_blocked_user_id(gateway: Any, user_id: str) -> bool:
    return is_blocked_user_id(gateway.config, user_id)


def is_blocked_group_id(config: Any, group_id: str) -> bool:
    group_id = safe_str(group_id).strip()
    return bool(group_id and group_id in config.blocked_group_ids)


def gateway_is_blocked_group_id(gateway: Any, group_id: str) -> bool:
    return is_blocked_group_id(gateway.config, group_id)


def is_trusted_user_id(config: Any, user_id: str) -> bool:
    user_id = safe_str(user_id).strip()
    if not user_id or user_id in config.owner_user_ids:
        return False
    return user_id in config.trusted_user_ids or user_id in config.whitelist_user_ids


def gateway_is_trusted_user_id(gateway: Any, user_id: str) -> bool:
    return is_trusted_user_id(gateway.config, user_id)


def trust_level_for_user_id(config: Any, user_id: str) -> str:
    user_id = safe_str(user_id).strip()
    if user_id in config.owner_user_ids:
        return "owner"
    if is_trusted_user_id(config, user_id):
        return "trusted"
    return "external"


def gateway_trust_level_for_user_id(gateway: Any, user_id: str) -> str:
    return trust_level_for_user_id(gateway.config, user_id)


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


def gateway_trust_command_target(gateway: Any, prepared: Any) -> tuple[str, str]:
    return trust_command_target(prepared, owner_user_ids=gateway.config.owner_user_ids)


def group_shadow_group_allowed(config: Any, group_id: str) -> bool:
    group_id = safe_str(group_id).strip()
    allowed = set(config.group_shadow_allowed_group_ids)
    return bool(group_id and group_id in allowed)


def gateway_group_shadow_group_allowed(gateway: Any, group_id: str) -> bool:
    return group_shadow_group_allowed(gateway.config, group_id)
