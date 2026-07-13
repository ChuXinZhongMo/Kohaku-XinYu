"""Pure group / learning policy helpers for NativeQQGateway.

Kept free of gateway instance state so they can be unit-tested and reused
without constructing websockets or CoreBridgeClient.
"""
from __future__ import annotations

from typing import Any, Container

from xinyu_qq_gateway_utils import safe_str as _safe_str


def group_followup_key(*, group_id: str, user_id: str) -> str:
    return f"{_safe_str(group_id).strip()}:{_safe_str(user_id).strip()}"


def event_group_interest_observation(event: dict[str, Any]) -> dict[str, Any]:
    observed = event.get("_xinyu_group_interest_observation")
    return observed if isinstance(observed, dict) else {}


def group_interest_reply_group_allowed(
    group_id: str,
    *,
    allowed_group_ids: Container[str],
    interest_allowed_group_ids: Container[str],
    shadow_group_allowed: bool,
) -> bool:
    clean = _safe_str(group_id).strip()
    if not clean:
        return False
    if allowed_group_ids and clean not in allowed_group_ids:
        return False
    if interest_allowed_group_ids:
        return clean in interest_allowed_group_ids
    return shadow_group_allowed


def file_learning_group_allowed(
    group_id: str,
    *,
    allowed_group_ids: Container[str],
    file_learning_allowed_group_ids: Container[str],
) -> bool:
    clean = _safe_str(group_id).strip()
    if not clean:
        return False
    if allowed_group_ids and clean not in allowed_group_ids:
        return False
    return bool(file_learning_allowed_group_ids and clean in file_learning_allowed_group_ids)


def file_learning_scope_reject_reason(
    *,
    message_kind: str,
    sender_id: str,
    group_id: str,
    private_owner_only: bool,
    owner_user_ids: Container[str],
    allowed_group_ids: Container[str],
    file_learning_allowed_group_ids: Container[str],
    sender_is_trusted: bool,
) -> str:
    if not private_owner_only:
        return ""
    clean_sender = _safe_str(sender_id).strip()
    if message_kind == "private":
        return "" if clean_sender in owner_user_ids else "file_learning_private_owner_only"
    if message_kind != "group":
        return "file_learning_private_owner_only"
    if not file_learning_group_allowed(
        group_id,
        allowed_group_ids=allowed_group_ids,
        file_learning_allowed_group_ids=file_learning_allowed_group_ids,
    ):
        return "file_learning_group_not_allowed"
    if clean_sender in owner_user_ids or sender_is_trusted:
        return ""
    return "file_learning_sender_not_trusted"
