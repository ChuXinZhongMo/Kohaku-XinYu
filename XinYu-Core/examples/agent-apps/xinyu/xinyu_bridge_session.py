from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from xinyu_bridge_session_cleanup import (
    cleanup_idle_sessions as _cleanup_idle_sessions,
    session_keys_to_expire as _session_keys_to_expire,
    stop_all_sessions as _stop_all_sessions,
)
from xinyu_bridge_session_keys import (
    _safe_text as _session_safe_text,
    session_key_from_payload as _session_key_from_payload,
)
from xinyu_bridge_session_lifecycle import get_or_create_session as _get_or_create_session
from xinyu_bridge_session_model import AgentSession
from xinyu_bridge_session_runtime_bindings import (
    RuntimeSessionBindings,
    runtime_append_dialogue_tail_bound as _runtime_append_dialogue_tail_bound,
    runtime_append_sticker_delivery_tail_bound as _runtime_append_sticker_delivery_tail_bound,
    runtime_cleanup_idle_sessions_bound as _runtime_cleanup_idle_sessions_bound,
    runtime_get_session_bound as _runtime_get_session_bound,
)
from xinyu_bridge_session_runtime import (
    dialogue_tail_user_content_for_runtime as _dialogue_tail_user_content_for_runtime,
)
from xinyu_dialogue_working_memory import save_dialogue_tail


def _runtime_session_bindings() -> RuntimeSessionBindings:
    return RuntimeSessionBindings(
        cleanup_idle_sessions=cleanup_idle_sessions,
        get_or_create_session=get_or_create_session,
        save_dialogue_tail=save_dialogue_tail,
    )


def session_key_from_payload(payload: Mapping[str, Any]) -> str:
    return _session_key_from_payload(payload)


def session_keys_to_expire(
    sessions: Mapping[str, AgentSession],
    *,
    now: float,
    idle_ttl_seconds: int,
    max_sessions: int,
    preserve_keys: set[str] | None = None,
) -> set[str]:
    return _session_keys_to_expire(
        sessions,
        now=now,
        idle_ttl_seconds=idle_ttl_seconds,
        max_sessions=max_sessions,
        preserve_keys=preserve_keys,
    )


async def cleanup_idle_sessions(
    sessions: dict[str, AgentSession],
    sessions_lock: Any,
    *,
    idle_ttl_seconds: int,
    max_sessions: int,
    preserve_keys: set[str] | None = None,
    stop_timeout_seconds: int = 30,
    log_prefix: str = "[xinyu_core_bridge]",
) -> dict[str, int]:
    return await _cleanup_idle_sessions(
        sessions,
        sessions_lock,
        idle_ttl_seconds=idle_ttl_seconds,
        max_sessions=max_sessions,
        preserve_keys=preserve_keys,
        stop_timeout_seconds=stop_timeout_seconds,
        log_prefix=log_prefix,
        expire_key_provider=session_keys_to_expire,
    )


async def runtime_cleanup_idle_sessions(
    runtime: Any,
    *,
    preserve_keys: set[str] | None = None,
) -> dict[str, int]:
    return await _runtime_cleanup_idle_sessions_bound(
        runtime,
        preserve_keys=preserve_keys,
        bindings=_runtime_session_bindings(),
    )


def runtime_append_dialogue_tail(
    runtime: Any,
    session: AgentSession,
    *,
    user_text: str,
    reply: str,
    payload: dict[str, Any] | None = None,
) -> None:
    _runtime_append_dialogue_tail_bound(
        runtime,
        session,
        user_text=user_text,
        reply=reply,
        payload=payload,
        bindings=_runtime_session_bindings(),
    )


def runtime_dialogue_tail_user_content(
    runtime: Any,
    user_text: str,
    *,
    payload: dict[str, Any] | None = None,
) -> str:
    return _dialogue_tail_user_content_for_runtime(runtime, user_text, payload=payload)


def runtime_append_sticker_delivery_tail(
    runtime: Any,
    session: AgentSession,
    sticker_reply: dict[str, Any],
) -> bool:
    return _runtime_append_sticker_delivery_tail_bound(
        runtime,
        session,
        sticker_reply,
        bindings=_runtime_session_bindings(),
    )


async def stop_all_sessions(
    sessions: dict[str, AgentSession],
    sessions_lock: Any,
    *,
    stop_timeout_seconds: int = 30,
    log_prefix: str = "[xinyu_core_bridge]",
) -> dict[str, int]:
    return await _stop_all_sessions(
        sessions,
        sessions_lock,
        stop_timeout_seconds=stop_timeout_seconds,
        log_prefix=log_prefix,
    )


async def get_or_create_session(
    session_key: str,
    sessions: dict[str, AgentSession],
    sessions_lock: Any,
    *,
    xinyu_dir: Any,
    agent_cls: Any,
    input_module_factory: Callable[[], Any],
    load_runtime: Callable[[], Any],
    ensure_context_health: Callable[[Any], Any],
    prompt_signature_provider: Callable[[], str],
    dialogue_tail_loader: Callable[..., list[dict[str, str]]],
    dialogue_session_tail_entries: int,
    stop_timeout_seconds: int = 30,
    log_prefix: str = "[xinyu_core_bridge]",
) -> AgentSession:
    return await _get_or_create_session(
        session_key,
        sessions,
        sessions_lock,
        xinyu_dir=xinyu_dir,
        agent_cls=agent_cls,
        input_module_factory=input_module_factory,
        load_runtime=load_runtime,
        ensure_context_health=ensure_context_health,
        prompt_signature_provider=prompt_signature_provider,
        dialogue_tail_loader=dialogue_tail_loader,
        dialogue_session_tail_entries=dialogue_session_tail_entries,
        stop_timeout_seconds=stop_timeout_seconds,
        log_prefix=log_prefix,
    )


async def runtime_get_session(
    runtime: Any,
    session_key: str,
    *,
    input_module_factory: Callable[[], Any],
    ensure_context_health: Callable[[Any], Any],
    dialogue_tail_loader: Callable[..., list[dict[str, str]]],
) -> AgentSession:
    return await _runtime_get_session_bound(
        runtime,
        session_key,
        input_module_factory=input_module_factory,
        ensure_context_health=ensure_context_health,
        dialogue_tail_loader=dialogue_tail_loader,
        bindings=_runtime_session_bindings(),
    )


def _safe_text(value: Any) -> str:
    return _session_safe_text(value)
