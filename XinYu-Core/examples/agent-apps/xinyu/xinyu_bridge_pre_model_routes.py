from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from xinyu_bridge_pre_model_state import PreModelRouteResult
from xinyu_human_voice_flags import bypass_model_enabled
from xinyu_memory_event_sourcing import record_chat_event
from xinyu_reply_source import FinalTextSource, note_for_final_text_source


def _tag_functional_source(event_sidecar: dict[str, Any]) -> None:
    """Mark a pre-model functional-composer win for provenance (plan 11.7/11.9).

    These routes (runtime status, action results, codex, digests) carry real
    facts and keep their structured composer; we only tag them so the canned-vs
    -model accounting can tell them apart from a pretend-chat constant. Gated so
    flag-off output is unchanged.
    """

    if not bypass_model_enabled():
        return
    note = note_for_final_text_source(FinalTextSource.FUNCTIONAL_COMPOSER)
    notes = event_sidecar.setdefault("notes", [])
    if note not in notes:
        notes.append(note)


async def run_pre_model_routes(
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
    runtime_repair_status_func: Callable[..., Any],
    tinykernel_shadow_func: Callable[..., Any],
    event_recorder_func: Callable[..., dict[str, Any]] = record_chat_event,
    to_thread_func: Callable[..., Any] = asyncio.to_thread,
) -> PreModelRouteResult:
    event_sidecar: dict[str, Any] = {"notes": ["event_sourcing_not_run"]}
    v1_shadow: dict[str, Any] = {"notes": []}
    try:
        from xinyu_bridge_kernel_turn import inject_kernel_pre_turn_context

        inject_kernel_pre_turn_context(runtime, payload)
    except Exception:
        pass
    try:
        event_sidecar = await to_thread_func(event_recorder_func, runtime.xinyu_dir, payload, text=text)
    except Exception as exc:
        print(f"[xinyu_core_bridge] event sourcing sidecar failed: {exc}", flush=True)
        event_sidecar = {"notes": [f"event_sourcing_error:{type(exc).__name__}"]}

    runtime_status_response = await runtime_repair_status_func(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
    )
    if runtime_status_response is not None:
        _tag_functional_source(event_sidecar)
        return PreModelRouteResult(runtime_status_response, event_sidecar, v1_shadow)

    action_layer_response = await runtime._maybe_handle_action_layer_turn(
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
    )
    if action_layer_response is not None:
        _tag_functional_source(event_sidecar)
        return PreModelRouteResult(action_layer_response, event_sidecar, v1_shadow)

    recent_action_followup = await runtime._maybe_handle_recent_action_followup_turn(
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
    )
    if recent_action_followup is not None:
        _tag_functional_source(event_sidecar)
        return PreModelRouteResult(recent_action_followup, event_sidecar, v1_shadow)

    action_digest_followup = await runtime._maybe_handle_action_digest_followup_turn(
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
    )
    if action_digest_followup is not None:
        _tag_functional_source(event_sidecar)
        return PreModelRouteResult(action_digest_followup, event_sidecar, v1_shadow)

    v1_canary_response = await runtime._maybe_handle_v1_canary_turn(
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
    )
    if v1_canary_response is not None:
        _tag_functional_source(event_sidecar)
        return PreModelRouteResult(v1_canary_response, event_sidecar, v1_shadow)

    v1_shadow = await runtime._run_v1_shadow(payload, text=text)
    tinykernel_shadow = await tinykernel_shadow_func(
        runtime,
        payload,
        text=text,
        turn_id=turn_id,
        observed_at=turn_started_wall,
    )
    return PreModelRouteResult(None, event_sidecar, v1_shadow, tinykernel_shadow)
