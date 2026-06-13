from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Mapping
from typing import Any

from xinyu_bridge_session_model import AgentSession


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


async def cleanup_idle_sessions(
    sessions: dict[str, AgentSession],
    sessions_lock: Any,
    *,
    idle_ttl_seconds: int,
    max_sessions: int,
    preserve_keys: set[str] | None = None,
    stop_timeout_seconds: int = 30,
    log_prefix: str = "[xinyu_core_bridge]",
    expire_key_provider: Callable[..., set[str]] = session_keys_to_expire,
) -> dict[str, int]:
    preserve_keys = set(preserve_keys or set())
    if idle_ttl_seconds <= 0 and max_sessions <= 0:
        return {"cleaned_sessions": 0, "remaining_sessions": len(sessions)}

    to_stop: list[AgentSession] = []
    async with sessions_lock:
        expire_keys = expire_key_provider(
            sessions,
            now=time.time(),
            idle_ttl_seconds=idle_ttl_seconds,
            max_sessions=max_sessions,
            preserve_keys=preserve_keys,
        )
        for key in expire_keys:
            session = sessions.pop(key, None)
            if session is not None:
                to_stop.append(session)
        remaining_count = len(sessions)

    for session in to_stop:
        try:
            await asyncio.wait_for(session.agent.stop(), timeout=stop_timeout_seconds)
            print(f"{log_prefix} cleaned idle session {session.key}", flush=True)
        except Exception as exc:
            print(f"{log_prefix} failed to clean session {session.key}: {exc}", flush=True)

    return {"cleaned_sessions": len(to_stop), "remaining_sessions": remaining_count}


async def runtime_cleanup_idle_sessions(
    runtime: Any,
    *,
    preserve_keys: set[str] | None = None,
    cleanup_idle_sessions_func: Callable[..., Any] = cleanup_idle_sessions,
) -> dict[str, int]:
    preserved = set(preserve_keys or set())
    if runtime.autonomous_maintenance_enabled and runtime.autonomous_maintenance_session_key:
        preserved.add(runtime.autonomous_maintenance_session_key)
    return await cleanup_idle_sessions_func(
        runtime._sessions,
        runtime._sessions_lock,
        idle_ttl_seconds=runtime.session_idle_ttl_seconds,
        max_sessions=runtime.max_sessions,
        preserve_keys=preserved,
    )


async def stop_all_sessions(
    sessions: dict[str, AgentSession],
    sessions_lock: Any,
    *,
    stop_timeout_seconds: int = 30,
    log_prefix: str = "[xinyu_core_bridge]",
) -> dict[str, int]:
    async with sessions_lock:
        to_stop = list(sessions.values())
        sessions.clear()

    stopped_sessions = 0
    failed_sessions = 0
    for session in to_stop:
        try:
            await asyncio.wait_for(session.agent.stop(), timeout=stop_timeout_seconds)
            stopped_sessions += 1
        except Exception as exc:
            failed_sessions += 1
            print(f"{log_prefix} failed to stop session {session.key}: {exc}", flush=True)

    return {
        "stopped_sessions": stopped_sessions,
        "failed_sessions": failed_sessions,
        "remaining_sessions": len(sessions),
    }
