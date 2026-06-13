from __future__ import annotations

import time
from http import HTTPStatus
from typing import Any

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_slow_live_turn import run_slow_live_turn_from_pre_model_phase_with_trace
from xinyu_bridge_turn_pipeline import (
    run_pre_model_phase_with_trace,
    start_chat_turn_with_trace,
    try_initial_semantic_fast_route_with_trace,
)
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_chat_service import ChatServiceError


async def run_chat_payload(runtime: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if runtime._closed:
        raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
    try:
        chat_request = runtime.chat_service.prepare_request(
            payload,
            max_text_chars=runtime.max_text_chars,
            payload_text=runtime._payload_text,
            session_key=runtime._session_key,
        )
    except ChatServiceError as exc:
        raise BridgeRequestError(exc.status, exc.message) from exc
    if chat_request.empty_response is not None:
        return chat_request.empty_response

    turn_clock = runtime.chat_service.start_turn_clock()
    turn_started_wall = turn_clock.started_wall
    return await run_chat_turn_after_request_with_trace(
        runtime,
        payload,
        text=chat_request.text,
        session_key=chat_request.session_key,
        turn_started_at=turn_clock.started_at,
        turn_started_wall=turn_started_wall,
        turn_event_time=runtime._payload_event_time_iso(payload, fallback=turn_started_wall),
        turn_event_timestamp=runtime._payload_event_timestamp_seconds(payload, fallback=int(time.time())),
    )


async def run_chat_turn_after_request_with_trace(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_started_at: float,
    turn_started_wall: str,
    turn_event_time: str,
    turn_event_timestamp: int,
) -> dict[str, Any]:
    async with runtime._global_turn_lock:
        cleanup = await runtime._cleanup_idle_sessions()
        turn_start = start_chat_turn_with_trace(
            runtime,
            payload,
            text=text,
            session_key=session_key,
            turn_started_at=turn_started_at,
        )
        presence_start = turn_start["presence_start"]
        turn_id = turn_start["turn_id"]
        trace_route_stage = turn_start["trace_route_stage"]
        initial_semantic_fast = await try_initial_semantic_fast_route_with_trace(
            runtime,
            payload,
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            cleanup=cleanup,
            trace_route_stage=trace_route_stage,
        )
        if initial_semantic_fast["response"] is not None:
            return initial_semantic_fast["response"]

        pre_model_phase = await run_pre_model_phase_with_trace(
            runtime,
            payload,
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            cleanup=cleanup,
            desktop_started_published=initial_semantic_fast["desktop_started_published"],
            timeout_seconds=runtime.pre_model_routes_timeout_seconds,
            trace_route_stage=trace_route_stage,
        )
        if pre_model_phase["response"] is not None:
            return pre_model_phase["response"]

        publish_turn_id = _safe_str(presence_start.get("turn_id"))
        return await run_slow_live_turn_from_pre_model_phase_with_trace(
            runtime,
            payload,
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            publish_turn_id=publish_turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            turn_event_time=turn_event_time,
            turn_event_timestamp=turn_event_timestamp,
            pre_model_phase=pre_model_phase,
            cleanup=cleanup,
            settle_seconds=runtime.settle_seconds,
            trace_route_stage=trace_route_stage,
        )
