from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from xinyu_bridge_session_model import AgentSession
from xinyu_bridge_session_runtime import (
    append_dialogue_tail_for_runtime,
    append_sticker_delivery_tail_for_runtime,
    cleanup_idle_sessions_for_runtime,
    get_session_for_runtime,
)


@dataclass(frozen=True, slots=True)
class RuntimeSessionBindings:
    cleanup_idle_sessions: Callable[..., Any]
    get_or_create_session: Callable[..., Any]
    save_dialogue_tail: Callable[..., Any]


async def runtime_cleanup_idle_sessions_bound(
    runtime: Any,
    *,
    bindings: RuntimeSessionBindings,
    preserve_keys: set[str] | None = None,
) -> dict[str, int]:
    return await cleanup_idle_sessions_for_runtime(
        runtime,
        preserve_keys=preserve_keys,
        cleanup_idle_sessions_func=bindings.cleanup_idle_sessions,
    )


def runtime_append_dialogue_tail_bound(
    runtime: Any,
    session: AgentSession,
    *,
    bindings: RuntimeSessionBindings,
    user_text: str,
    reply: str,
    payload: dict[str, Any] | None = None,
) -> None:
    append_dialogue_tail_for_runtime(
        runtime,
        session,
        user_text=user_text,
        reply=reply,
        payload=payload,
        save_dialogue_tail_func=bindings.save_dialogue_tail,
    )


def runtime_append_sticker_delivery_tail_bound(
    runtime: Any,
    session: AgentSession,
    sticker_reply: dict[str, Any],
    *,
    bindings: RuntimeSessionBindings,
) -> bool:
    return append_sticker_delivery_tail_for_runtime(
        runtime,
        session,
        sticker_reply,
        save_dialogue_tail_func=bindings.save_dialogue_tail,
    )


async def runtime_get_session_bound(
    runtime: Any,
    session_key: str,
    *,
    bindings: RuntimeSessionBindings,
    input_module_factory: Callable[[], Any],
    ensure_context_health: Callable[[Any], Any],
    dialogue_tail_loader: Callable[..., list[dict[str, str]]],
) -> AgentSession:
    return await get_session_for_runtime(
        runtime,
        session_key,
        input_module_factory=input_module_factory,
        ensure_context_health=ensure_context_health,
        dialogue_tail_loader=dialogue_tail_loader,
        get_or_create_session_func=bindings.get_or_create_session,
    )
