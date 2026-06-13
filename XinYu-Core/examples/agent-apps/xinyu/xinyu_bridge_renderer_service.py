from __future__ import annotations

import asyncio
from typing import Any

from xinyu_bridge_renderer_payload import normalize_reply


async def render_outward_reply_impl(
    renderer: Any,
    agent: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    draft_reply: str,
    canonical_recall_context: str = "",
) -> str:
    llm = getattr(agent, "llm", None)
    if llm is None:
        return draft_reply

    messages = renderer.build_renderer_messages(
        agent,
        payload=payload,
        user_text=user_text,
        draft_reply=draft_reply,
        canonical_recall_context=canonical_recall_context,
    )
    try:
        response = await asyncio.wait_for(
            llm.chat_complete(messages, temperature=0.55, max_tokens=520),
            timeout=renderer.render_timeout_seconds,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] outward renderer failed: {type(exc).__name__}: {exc}", flush=True)
        return draft_reply

    rendered = normalize_reply(getattr(response, "content", "") or "")
    rendered = renderer.strip_renderer_wrappers(rendered) or draft_reply

    quality_flags = renderer.speech_controller.reply_quality_flags(
        payload=payload,
        user_text=user_text,
        reply=rendered,
    )
    if quality_flags:
        retry_messages = renderer.build_renderer_messages(
            agent,
            payload=payload,
            user_text=user_text,
            draft_reply=draft_reply,
            canonical_recall_context=canonical_recall_context,
            failed_reply=rendered,
            quality_flags=quality_flags,
        )
        try:
            retry_response = await asyncio.wait_for(
                llm.chat_complete(retry_messages, temperature=0.45, max_tokens=180),
                timeout=renderer.render_timeout_seconds,
            )
        except Exception as exc:
            print(f"[xinyu_core_bridge] outward renderer retry failed: {type(exc).__name__}: {exc}", flush=True)
            return rendered

        retry_rendered = normalize_reply(getattr(retry_response, "content", "") or "")
        retry_rendered = renderer.strip_renderer_wrappers(retry_rendered)
        if retry_rendered:
            retry_flags = renderer.speech_controller.reply_quality_flags(
                payload=payload,
                user_text=user_text,
                reply=retry_rendered,
            )
            if retry_flags:
                return rendered
            print(
                f"[xinyu_core_bridge] outward renderer retry applied: {', '.join(quality_flags)}",
                flush=True,
            )
            return retry_rendered

    return rendered
