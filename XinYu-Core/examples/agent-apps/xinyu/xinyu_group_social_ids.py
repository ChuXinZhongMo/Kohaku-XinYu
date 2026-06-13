"""Stable identity + hashing for group social memory (plan §4.1 / §5.1).

Same QQ user is isolated across groups (the group id is part of the member
identity), and the same group/user is stable. Long-term files store only the
hashes returned here; raw QQ group/user/message ids never reach disk through
this module.
"""

from __future__ import annotations

import hashlib

_HASH_PREFIX = "sha256:"
_HASH_LEN = 32  # truncated hex; enough to avoid collisions, short enough to log

# Sentinels for missing ids — never crash, never invent a hash from emptiness.
UNKNOWN_GROUP = "unknown_group"
UNKNOWN_MEMBER = "unknown_member"
UNKNOWN_MESSAGE = "unknown_message"


def _norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def _platform(value: object) -> str:
    return _norm(value).lower() or "qq"


def _digest(identity: str) -> str:
    return _HASH_PREFIX + hashlib.sha256(identity.encode("utf-8", errors="replace")).hexdigest()[:_HASH_LEN]


def group_identity(platform: str, group_id: str) -> str:
    return f"{_platform(platform)}:group:{_norm(group_id)}"


def group_member_identity(platform: str, group_id: str, user_id: str) -> str:
    return f"{group_identity(platform, group_id)}:user:{_norm(user_id)}"


def message_identity(platform: str, group_id: str, message_id: str) -> str:
    return f"{group_identity(platform, group_id)}:message:{_norm(message_id)}"


def group_hash(platform: str, group_id: str) -> str:
    if not _norm(group_id):
        return UNKNOWN_GROUP
    return _digest(group_identity(platform, group_id))


def group_member_hash(platform: str, group_id: str, user_id: str) -> str:
    # A member is only meaningful inside a known group; missing either id ->
    # unknown so two unknowns never merge into one bogus member.
    if not _norm(group_id) or not _norm(user_id):
        return UNKNOWN_MEMBER
    return _digest(group_member_identity(platform, group_id, user_id))


def message_hash(platform: str, group_id: str, message_id: str) -> str:
    if not _norm(group_id) or not _norm(message_id):
        return UNKNOWN_MESSAGE
    return _digest(message_identity(platform, group_id, message_id))


def is_known_hash(value: str) -> bool:
    return bool(value) and value.startswith(_HASH_PREFIX)


def path_segment(hash_value: str) -> str:
    """Filesystem-safe segment for a hash (drops the ``sha256:`` prefix's colon)."""

    return _norm(hash_value).replace(":", "_") or "unknown"
