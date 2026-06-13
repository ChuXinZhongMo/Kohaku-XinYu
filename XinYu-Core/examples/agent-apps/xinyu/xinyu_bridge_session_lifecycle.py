from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from xinyu_bridge_session_model import AgentSession


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
    load_runtime()
    ensure_context_health(xinyu_dir)
    prompt_signature = prompt_signature_provider()
    old_session: AgentSession | None = None
    async with sessions_lock:
        session = sessions.get(session_key)
        if session is not None and session.prompt_signature == prompt_signature:
            return session
        if session is not None:
            old_session = sessions.pop(session_key)

    if old_session is not None:
        try:
            await asyncio.wait_for(old_session.agent.stop(), timeout=stop_timeout_seconds)
            print(
                f"{log_prefix} restarted session {session_key} after prompt/memory context change",
                flush=True,
            )
        except Exception as exc:
            print(f"{log_prefix} failed to stop stale session {session_key}: {exc}", flush=True)

    if dialogue_session_tail_entries <= 0:
        dialogue_tail = []
    elif old_session is not None and old_session.dialogue_tail:
        dialogue_tail = list(old_session.dialogue_tail[-dialogue_session_tail_entries:])
    else:
        dialogue_tail = dialogue_tail_loader(
            xinyu_dir,
            session_key,
            max_entries=dialogue_session_tail_entries,
            include_timestamps=True,
        )

    chunks: list[str] = []
    agent = agent_cls.from_path(
        str(xinyu_dir),
        input_module=input_module_factory(),
        pwd=str(xinyu_dir),
    )
    agent.set_output_handler(
        lambda text, buffer=chunks: buffer.append(text),
        replace_default=True,
    )
    await agent.start()
    ensure_context_health(xinyu_dir)
    session = AgentSession(
        key=session_key,
        agent=agent,
        prompt_signature=prompt_signature,
        chunks=chunks,
        dialogue_tail=dialogue_tail,
    )
    async with sessions_lock:
        sessions[session_key] = session
    print(f"{log_prefix} started session {session_key}", flush=True)
    return session
