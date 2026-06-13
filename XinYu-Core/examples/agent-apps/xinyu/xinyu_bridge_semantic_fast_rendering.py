from __future__ import annotations

from contextlib import nullcontext
from typing import Any


async def render_owner_private_semantic_fast_reply(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session: Any | None,
    session_key: str,
    turn_id: str,
    decision: dict[str, Any],
    empty_state_notice_func: Any,
    provider_failover_context_func: Any,
    safe_str_func: Any,
    failover_context_func: Any = None,
) -> tuple[str, str] | None:
    renderer_name = "direct"
    reply = safe_str_func(decision.get("direct_reply")).strip()
    if reply:
        return reply, renderer_name
    if session is None:
        return None

    renderer_name = "outward_reply"
    try:
        llm = getattr(session.agent, "llm", None)
        failover_context = _build_failover_context(
            runtime,
            payload,
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            failover_context_func=failover_context_func,
        )
        context_manager = (
            provider_failover_context_func(llm, failover_context)
            if llm is not None and failover_context
            else nullcontext()
        )
        with context_manager:
            rendered = await runtime._render_outward_reply(
                session.agent,
                payload=payload,
                user_text=text,
                draft_reply="",
                canonical_recall_context="",
            )
    except Exception as exc:
        print(f"[xinyu_core_bridge] semantic fast renderer failed: {type(exc).__name__}: {exc}", flush=True)
        return None

    reply = safe_str_func(rendered).strip()
    if reply:
        return reply, renderer_name

    # Model produced nothing: prefer the demoted canned line carried by the
    # decision (plan 11.5), else recompute the empty-state notice. Both are
    # last-resort constants.
    canned_fallback = safe_str_func(decision.get("canned_fallback")).strip()
    if canned_fallback:
        return canned_fallback, "canned_fallback"

    reply = empty_state_notice_func(text, seed=turn_id)
    if not reply:
        return None
    return reply, "empty_state_notice"


def _build_failover_context(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    failover_context_func: Any = None,
) -> dict[str, Any] | None:
    failover_builder = getattr(runtime, "_owner_private_llm_failover_context", None)
    if callable(failover_builder):
        try:
            return failover_builder(
                payload,
                text=text,
                session_key=session_key,
                turn_id=turn_id,
            )
        except Exception:
            return None
    if callable(failover_context_func):
        try:
            return failover_context_func(
                runtime,
                payload,
                text=text,
                session_key=session_key,
                turn_id=turn_id,
            )
        except Exception:
            return None
    return None
