from __future__ import annotations

from typing import Any


def runtime_renderer_reason(runtime: Any, *, payload: dict[str, Any], user_text: str, draft_reply: str) -> str:
    return runtime.renderer.renderer_reason(payload=payload, user_text=user_text, draft_reply=draft_reply)


def runtime_build_renderer_messages(
    runtime: Any,
    agent: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    draft_reply: str,
    canonical_recall_context: str = "",
    failed_reply: str = "",
    quality_flags: list[str] | None = None,
) -> list[dict[str, str]]:
    return runtime.renderer.build_renderer_messages(
        agent,
        payload=payload,
        user_text=user_text,
        draft_reply=draft_reply,
        canonical_recall_context=canonical_recall_context,
        failed_reply=failed_reply,
        quality_flags=quality_flags,
    )


def runtime_renderer_memory_context(runtime: Any) -> str:
    return runtime.renderer.renderer_memory_context()


def runtime_read_text(runtime: Any, rel: str, *, limit: int) -> str:
    return runtime.renderer.read_text(rel, limit=limit)


def runtime_conversation_tail(runtime: Any, agent: Any, *, max_messages: int) -> str:
    return runtime.renderer.conversation_tail(agent, max_messages=max_messages)


def runtime_strip_renderer_wrappers(runtime: Any, text: str) -> str:
    return runtime.renderer.strip_renderer_wrappers(text)
