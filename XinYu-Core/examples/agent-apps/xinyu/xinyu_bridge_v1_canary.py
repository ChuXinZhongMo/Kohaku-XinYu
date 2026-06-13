from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from xinyu_bridge_v1_payloads import (
    build_canary_notes,
    build_canary_response,
    command_id,
    owner_canary_payload,
    safe_str,
)


def canary_payload_allowed_impl(
    runtime: Any,
    payload: dict[str, Any],
    text: str,
    *,
    canary_gate_func: Callable[..., tuple[bool, list[str]]],
    owner_simple_canary_env: str,
    greeting_texts: frozenset[str],
    ack_texts: frozenset[str],
) -> tuple[bool, list[str]]:
    return canary_gate_func(
        v1_enabled=runtime.v1_enabled,
        owner_simple_canary=runtime.v1_owner_simple_canary,
        owner_private=runtime._owner_private_payload_matches(payload),
        payload=payload,
        text=text,
        owner_simple_canary_env=owner_simple_canary_env,
        greeting_texts=greeting_texts,
        ack_texts=ack_texts,
    )


async def handle_canary_turn_impl(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
    canary_payload_allowed_func: Callable[[Any, dict[str, Any], str], tuple[bool, list[str]]],
    ensure_app_func: Callable[[Any], Any],
    memory_snapshot_func: Callable[[Any], dict[str, Any]],
    record_turn_finished_func: Callable[..., Any],
    visible_text_hash_func: Callable[[str], str],
    timestamp_func: Callable[[Any], str],
    safe_str_func: Callable[[Any], str] = safe_str,
    command_id_func: Callable[[dict[str, Any]], str] = command_id,
) -> dict[str, Any] | None:
    allowed, canary_reasons = canary_payload_allowed_func(runtime, payload, text)
    if not allowed:
        return None

    started = time.perf_counter()
    try:
        app = ensure_app_func(runtime)
        v1_payload = owner_canary_payload(payload)
        turn = app.normalizer.normalize(v1_payload)
        decision = app.router.decide(turn)
        if getattr(decision.route, "value", "") != "fast_path":
            return None
        v1_reply = await asyncio.wait_for(app.handle_turn(turn), timeout=runtime.v1_canary_timeout_seconds)
    except Exception as exc:
        runtime._v1_last_error = f"{type(exc).__name__}: {exc}"
        print(f"[xinyu_core_bridge] v1 canary failed: {runtime._v1_last_error}", flush=True)
        return None

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    route = safe_str_func(getattr(v1_reply, "route", ""))
    trace_id = safe_str_func(getattr(v1_reply, "trace_id", ""))
    reply = safe_str_func(getattr(v1_reply, "reply", "")).strip()
    runtime._v1_last_error = ""
    runtime._v1_last_trace_id = trace_id
    runtime._v1_last_route = route
    if route != "fast_path" or not getattr(v1_reply, "accepted", False) or not reply:
        return None

    guarded_reply, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=text,
        reply=reply,
    )
    if guarded_reply:
        reply = guarded_reply

    notes = build_canary_notes(
        route=route,
        elapsed_ms=elapsed_ms,
        canary_reasons=canary_reasons,
        v1_reply=v1_reply,
        event_sidecar=event_sidecar,
        cleanup=cleanup,
        guard_flags=guard_flags,
        safe_str_func=safe_str_func,
    )
    after_memory = memory_snapshot_func(runtime.memory_root)
    memory_changed = before_memory != after_memory or bool(getattr(v1_reply, "memory_changed", False))
    total_elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
    record_turn_finished_func(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply=reply,
        elapsed_ms=total_elapsed_ms,
        status="ok",
        notes=notes,
        memory_changed=memory_changed,
    )
    reply_hash = visible_text_hash_func(reply)
    await runtime._desktop_publish_chat_finished(
        payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
        started_at=timestamp_func(turn_started_wall),
        elapsed_ms=total_elapsed_ms,
        status="ok",
        notes=notes,
        memory_changed=memory_changed,
        archive_message_ids=[],
        reply_hash=reply_hash,
        recall_event_id="",
        recall_count=0,
        top_recall_sources=[],
    )
    return build_canary_response(
        payload=payload,
        reply=reply,
        memory_changed=memory_changed,
        turn_id=turn_id,
        session_key=session_key,
        reply_hash=reply_hash,
        route=route,
        trace_id=trace_id,
        elapsed_ms=elapsed_ms,
        notes=notes,
        command_id_func=command_id_func,
    )
