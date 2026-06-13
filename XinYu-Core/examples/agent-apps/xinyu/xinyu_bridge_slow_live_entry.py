from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_slow_live_state import SlowLiveEntryState


TraceRouteStage = Callable[..., Any]


async def enter_slow_live_route_with_trace(
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
    trace_route_stage: TraceRouteStage,
    emotion_council_func: Callable[..., dict[str, Any]],
    semantic_fast_func: Callable[..., Any],
) -> SlowLiveEntryState:
    emotion_council = emotion_council_func(runtime, payload, text=text)
    session = await runtime._get_session(session_key)
    proactive_tail_synced = runtime._sync_recent_proactive_to_dialogue_tail(session, payload)
    semantic_fast_response = await semantic_fast_func(
        runtime,
        payload,
        text=text,
        session=session,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
        trace_route_stage=trace_route_stage,
    )
    return SlowLiveEntryState(
        response=semantic_fast_response,
        session=session,
        proactive_tail_synced=proactive_tail_synced,
        emotion_council=emotion_council,
    )
