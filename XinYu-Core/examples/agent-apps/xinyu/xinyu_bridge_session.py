from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentSession:
    key: str
    agent: Any
    prompt_signature: str
    chunks: list[str] = field(default_factory=list)
    dialogue_tail: list[dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)


def session_key_from_payload(payload: Mapping[str, Any]) -> str:
    for key in ("session_id", "user_id"):
        value = _safe_text(payload.get(key)).strip()
        if value:
            return value
    return "qq:default"


def session_keys_to_expire(
    sessions: Mapping[str, AgentSession],
    *,
    now: float,
    idle_ttl_seconds: int,
    max_sessions: int,
    preserve_keys: set[str] | None = None,
) -> set[str]:
    preserved = set(preserve_keys or set())
    if idle_ttl_seconds <= 0 and max_sessions <= 0:
        return set()

    expire_keys: set[str] = set()
    if idle_ttl_seconds > 0:
        for key, session in sessions.items():
            if key in preserved:
                continue
            if now - session.last_used_at > idle_ttl_seconds:
                expire_keys.add(key)

    remaining = [
        (key, session)
        for key, session in sessions.items()
        if key not in expire_keys and key not in preserved
    ]
    if max_sessions > 0 and len(sessions) - len(expire_keys) > max_sessions:
        overflow = len(sessions) - len(expire_keys) - max_sessions
        oldest = sorted(remaining, key=lambda item: item[1].last_used_at)[:overflow]
        expire_keys.update(key for key, _session in oldest)

    return expire_keys


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
