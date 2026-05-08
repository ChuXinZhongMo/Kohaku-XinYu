from __future__ import annotations

from typing import Any

from xinyu_bridge_values import as_bool, safe_str


def owner_private_payload_matches(payload: dict[str, Any]) -> bool:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    if not as_bool(metadata.get("is_owner_user"), default=False):
        return False
    message_type = safe_str(payload.get("message_type")).lower()
    return message_type.startswith("private") or not safe_str(payload.get("group_id")).strip()


def trusted_private_payload_matches(payload: dict[str, Any]) -> bool:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    if as_bool(metadata.get("is_owner_user"), default=False):
        return False
    if not as_bool(metadata.get("is_trusted_user"), default=False):
        return False
    message_type = safe_str(payload.get("message_type")).lower()
    if message_type and not message_type.startswith("private"):
        return False
    group_id = safe_str(payload.get("group_id")).strip()
    return group_id in {"", "0", "none", "None"}
