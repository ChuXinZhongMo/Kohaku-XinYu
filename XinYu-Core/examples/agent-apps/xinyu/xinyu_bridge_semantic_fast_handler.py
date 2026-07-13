from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from xinyu_bridge_semantic_fast_decision import owner_private_semantic_fast_decision_impl
from xinyu_bridge_semantic_fast_finish import finish_owner_private_semantic_fast_turn
from xinyu_bridge_semantic_fast_payloads import provider_failover_context, safe_str, timestamp_or_now_iso
from xinyu_bridge_semantic_fast_rendering import render_owner_private_semantic_fast_reply
from xinyu_bridge_semantic_fast_text import owner_private_empty_state_notice
from xinyu_turn_route_trace import record_turn_route_stage


async def handle_owner_private_semantic_fast_turn_impl(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session: Any | None,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any] | None,
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
    decision: dict[str, Any] | None = None,
    record_decision_stage: bool = True,
    decision_func: Callable[[Any, dict[str, Any], str], dict[str, Any]] = owner_private_semantic_fast_decision_impl,
    failover_context_func: Callable[..., dict[str, Any]] | None = None,
    empty_state_notice_func: Callable[..., str] = owner_private_empty_state_notice,
    provider_failover_context_func: Callable[..., Any] = provider_failover_context,
    safe_str_func: Callable[..., str] = safe_str,
    timestamp_func: Callable[..., str] = timestamp_or_now_iso,
) -> dict[str, Any] | None:
    started = time.perf_counter()
    if decision is None:
        try:
            decision = decision_func(runtime, payload, text)
        except Exception as exc:
            print(f"[xinyu_core_bridge] semantic fast route failed: {type(exc).__name__}: {exc}", flush=True)
            return None
    if not decision.get("allowed"):
        return None
    if record_decision_stage:
        record_turn_route_stage(
            runtime.xinyu_dir,
            turn_id=turn_id,
            stage="route_decided",
            route="owner_private_semantic_fast",
            status="accepted",
            elapsed_ms=int((time.perf_counter() - turn_started_at) * 1000),
            payload=payload,
            notes=[safe_str_func(note) for note in decision.get("notes", [])[:4]],
        )

    rendered = await render_owner_private_semantic_fast_reply(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        session=session,
        decision=decision,
        failover_context_func=failover_context_func,
        empty_state_notice_func=empty_state_notice_func,
        provider_failover_context_func=provider_failover_context_func,
        safe_str_func=safe_str_func,
    )
    if rendered is None:
        return None
    reply, renderer_name = rendered

    return await finish_owner_private_semantic_fast_turn(
        runtime,
        payload,
        text=text,
        session=session,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        semantic_started_at=started,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
        decision=decision,
        rendered_reply=reply,
        renderer_name=renderer_name,
        safe_str_func=safe_str_func,
        timestamp_func=timestamp_func,
    )
