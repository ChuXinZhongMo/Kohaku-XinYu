from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_session_cleanup import (
    runtime_cleanup_idle_sessions as _cleanup_idle_sessions_for_runtime,
)
from xinyu_bridge_session_model import AgentSession
from xinyu_bridge_session_tail import (
    append_dialogue_tail as _append_dialogue_tail,
    append_sticker_delivery_tail as _append_sticker_delivery_tail,
    dialogue_tail_user_content as _dialogue_tail_user_content,
)


async def cleanup_idle_sessions_for_runtime(
    runtime: Any,
    *,
    preserve_keys: set[str] | None = None,
    cleanup_idle_sessions_func: Callable[..., Any],
) -> dict[str, int]:
    return await _cleanup_idle_sessions_for_runtime(
        runtime,
        preserve_keys=preserve_keys,
        cleanup_idle_sessions_func=cleanup_idle_sessions_func,
    )


def append_dialogue_tail_for_runtime(
    runtime: Any,
    session: AgentSession,
    *,
    user_text: str,
    reply: str,
    save_dialogue_tail_func: Callable[..., Any],
    payload: dict[str, Any] | None = None,
) -> None:
    _append_dialogue_tail(
        runtime,
        session,
        user_text=user_text,
        reply=reply,
        payload=payload,
        save_dialogue_tail_func=save_dialogue_tail_func,
    )


def dialogue_tail_user_content_for_runtime(
    runtime: Any,
    user_text: str,
    *,
    payload: dict[str, Any] | None = None,
) -> str:
    return _dialogue_tail_user_content(user_text, payload=payload)


def append_sticker_delivery_tail_for_runtime(
    runtime: Any,
    session: AgentSession,
    sticker_reply: Any,
    *,
    save_dialogue_tail_func: Callable[..., Any],
) -> bool:
    return _append_sticker_delivery_tail(
        runtime,
        session,
        sticker_reply,
        save_dialogue_tail_func=save_dialogue_tail_func,
    )


async def get_session_for_runtime(
    runtime: Any,
    session_key: str,
    *,
    input_module_factory: Callable[[], Any],
    ensure_context_health: Callable[[Any], Any],
    dialogue_tail_loader: Callable[..., list[dict[str, str]]],
    get_or_create_session_func: Callable[..., Any],
) -> AgentSession:
    # Populate runtime state before snapshotting _agent_cls: on a cold start the
    # autonomous-maintenance timer reaches this path before any owner request has
    # triggered the bootstrap, so reading _agent_cls first would pass None into
    # Agent.from_path. _load_runtime is idempotent (guarded by runtime._loaded).
    runtime._load_runtime()
    return await get_or_create_session_func(
        session_key,
        runtime._sessions,
        runtime._sessions_lock,
        xinyu_dir=runtime.xinyu_dir,
        agent_cls=runtime._agent_cls,
        input_module_factory=input_module_factory,
        load_runtime=runtime._load_runtime,
        ensure_context_health=ensure_context_health,
        prompt_signature_provider=runtime._session_prompt_signature,
        dialogue_tail_loader=dialogue_tail_loader,
        dialogue_session_tail_entries=runtime.dialogue_session_tail_entries,
    )
