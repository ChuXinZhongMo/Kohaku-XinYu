from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


TraceRouteStage = Callable[..., Any]


async def run_slow_live_turn_from_pre_model_phase_with_trace(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    publish_turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    turn_event_time: str,
    turn_event_timestamp: int,
    pre_model_phase: Mapping[str, Any],
    cleanup: dict[str, Any],
    settle_seconds: float,
    trace_route_stage: TraceRouteStage,
    enter_func: Callable[..., Any],
    model_turn_func: Callable[..., Any],
    prepare_post_model_func: Callable[..., Any],
    finish_prepared_func: Callable[..., Any],
    sleep_func: Callable[..., Any],
) -> dict[str, Any]:
    slow_live_entry = await enter_func(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=publish_turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=pre_model_phase["before_memory"],
        cleanup=cleanup,
        event_sidecar=pre_model_phase["event_sidecar"],
        trace_route_stage=trace_route_stage,
    )
    if slow_live_entry["response"] is not None:
        return slow_live_entry["response"]

    session = slow_live_entry["session"]
    model_turn = await model_turn_func(
        runtime,
        payload,
        session=session,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        llm_failover_turn_id=publish_turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        turn_event_timestamp=turn_event_timestamp,
        evaluated_at=turn_event_time,
        curiosity_eval=pre_model_phase["curiosity_eval"],
        trace_route_stage=trace_route_stage,
    )

    if settle_seconds > 0:
        await sleep_func(settle_seconds)

    post_model_reply = await prepare_post_model_func(
        runtime,
        session,
        payload,
        text=text,
        session_key=session_key,
        model_turn=model_turn,
        evaluated_at=turn_event_time,
        trace_route_stage=trace_route_stage,
    )
    return await finish_prepared_func(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        publish_turn_id=publish_turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        pre_model_phase=pre_model_phase,
        slow_live_entry=slow_live_entry,
        model_turn=model_turn,
        post_model_reply=post_model_reply,
        cleanup=cleanup,
        trace_route_stage=trace_route_stage,
    )
