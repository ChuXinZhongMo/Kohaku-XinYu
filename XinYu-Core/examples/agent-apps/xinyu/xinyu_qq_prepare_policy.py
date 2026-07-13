"""Pure prepare_message rejection reasons for NativeQQGateway.

Gateway keeps orchestration (extract text/materials, group followup windows);
this module holds the scope checks that do not need instance state.
"""
from __future__ import annotations

from typing import Any, Container


def empty_message_reason(
    *,
    text: str,
    learning_material: Any,
    sticker_material: Any,
    rich_segments: Any,
) -> str | None:
    if text or learning_material is not None or sticker_material is not None:
        return None
    if rich_segments:
        return "rich_message_without_supported_route"
    return "empty_message"


def sticker_import_scope_reject_reason(
    *,
    enabled: bool,
    private_owner_only: bool,
    message_kind: str,
    sender_id: str,
    owner_user_ids: Container[str],
    has_sticker_material: bool,
) -> str | None:
    if not enabled or not has_sticker_material:
        return None
    if private_owner_only and (message_kind != "private" or sender_id not in owner_user_ids):
        return "sticker_import_private_owner_only"
    return None


def package_install_scope_reject_reason(
    *,
    package_text: str | None,
    enabled: bool,
    owner_private_only: bool,
    message_kind: str,
    sender_id: str,
    owner_user_ids: Container[str],
) -> str | None:
    if package_text is None:
        return None
    if not enabled:
        return "package_install_disabled"
    if owner_private_only and (message_kind != "private" or sender_id not in owner_user_ids):
        return "package_install_private_owner_only"
    return None


def codex_command_scope_reject_reason(
    *,
    codex_task: str | None,
    enabled: bool,
    message_kind: str,
    sender_id: str,
    owner_user_ids: Container[str],
) -> str | None:
    if codex_task is None:
        return None
    if not enabled:
        return "codex_command_disabled"
    if message_kind != "private":
        return "codex_private_only"
    if sender_id not in owner_user_ids:
        return "codex_owner_only"
    return None


def basic_channel_reject_reason(
    *,
    private_only: bool,
    message_kind: str,
    allow_group_messages: bool,
) -> str | None:
    """Top-level channel gates used by prepare_message."""
    if private_only and message_kind != "private":
        return "private_only"
    if message_kind == "group" and not allow_group_messages:
        return "group_disabled"
    return None


def owner_private_command_reject_reason(
    *,
    message_kind: str,
    sender_id: str,
    owner_user_ids: Container[str],
    reason: str = "owner_private_only",
) -> str | None:
    """Goldmark / review / self-action commands are owner-private only."""
    if message_kind != "private" or sender_id not in owner_user_ids:
        return reason
    return None


def learning_ingest_scope_reject_reason(
    *,
    enabled: bool,
    has_learning_material: bool,
    file_learning_reject_reason: str,
) -> str | None:
    """Return gateway ignore reason for QQ file learning, or None if allowed."""
    if not enabled or not has_learning_material:
        return None
    if file_learning_reject_reason:
        return file_learning_reject_reason
    return None
