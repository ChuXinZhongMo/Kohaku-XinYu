from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from xinyu_bridge_renderer_payload import _safe_str
from xinyu_runtime_context import build_renderer_memory_context, read_limited


def renderer_memory_context(
    xinyu_dir: Path,
    *,
    user_text: str = "",
    canonical_recall_context: str = "",
    build_context: Callable[..., str] = build_renderer_memory_context,
) -> str:
    return build_context(
        xinyu_dir,
        user_text=user_text,
        canonical_recall_context=canonical_recall_context,
    )


def read_text(
    xinyu_dir: Path,
    rel: str,
    *,
    limit: int,
    read_limited_func: Callable[..., str] = read_limited,
) -> str:
    return read_limited_func(xinyu_dir, rel, limit=limit)


def conversation_tail(agent: Any, *, max_messages: int) -> str:
    controller = getattr(agent, "controller", None)
    conversation = getattr(controller, "conversation", None)
    if conversation is None or not hasattr(conversation, "to_messages"):
        return ""
    try:
        messages = conversation.to_messages()
    except Exception:
        return ""

    lines: list[str] = []
    for message in messages[-max_messages:]:
        role = _safe_str(message.get("role"))
        if role == "system":
            continue
        content = message.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                _safe_str(part.get("text"))
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        content_text = _safe_str(content).strip()
        if content_text:
            recorded_at = _safe_str(message.get("recorded_at")).strip() if isinstance(message, dict) else ""
            time_suffix = f" ({recorded_at})" if recorded_at else ""
            lines.append(f"{role}{time_suffix}: {content_text[:1000]}")
    return "\n".join(lines)
