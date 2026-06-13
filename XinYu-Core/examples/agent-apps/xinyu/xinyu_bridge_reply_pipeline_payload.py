from __future__ import annotations

from typing import Any


async def runtime_render_outward_reply_impl(
    runtime: Any,
    agent: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    draft_reply: str,
    canonical_recall_context: str = "",
) -> str:
    return await runtime.renderer.render_outward_reply(
        agent,
        payload=payload,
        user_text=user_text,
        draft_reply=draft_reply,
        canonical_recall_context=canonical_recall_context,
    )
