from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from xinyu_bridge_slow_live_publish_service import (
    publish_slow_live_failed_turn as _publish_slow_live_failed_turn,
)
from xinyu_bridge_slow_live_publish_service import (
    publish_slow_live_success_turn as _publish_slow_live_success_turn,
)
from xinyu_bridge_time_utils import timestamp_or_now_iso
from xinyu_bridge_values import safe_str as _safe_str


TraceRouteStage = Callable[..., Any]


async def publish_slow_live_failed_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session: Any,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    status: str,
    notes: list[str],
    recalled_context_event: dict[str, Any],
    recalled_context: Any,
    clock_func: Callable[[], float] = time.perf_counter,
    timestamp_func: Callable[..., str] = timestamp_or_now_iso,
    safe_str_func: Callable[..., str] = _safe_str,
) -> int:
    return await _publish_slow_live_failed_turn(
        runtime,
        payload,
        session=session,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        status=status,
        notes=notes,
        recalled_context_event=recalled_context_event,
        recalled_context=recalled_context,
        clock_func=clock_func,
        timestamp_func=timestamp_func,
        safe_str_func=safe_str_func,
    )


async def publish_slow_live_success_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    reply: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: Any,
    after_memory: Any,
    notes: list[str],
    archive_result: dict[str, Any],
    recalled_context_event: dict[str, Any],
    recalled_context: Any,
    reply_bubble_force_units: list[int],
    trace_route_stage: TraceRouteStage,
    clock_func: Callable[[], float] = time.perf_counter,
    timestamp_func: Callable[..., str] = timestamp_or_now_iso,
    safe_str_func: Callable[..., str] = _safe_str,
) -> dict[str, Any]:
    return await _publish_slow_live_success_turn(
        runtime,
        payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        after_memory=after_memory,
        notes=notes,
        archive_result=archive_result,
        recalled_context_event=recalled_context_event,
        recalled_context=recalled_context,
        reply_bubble_force_units=reply_bubble_force_units,
        trace_route_stage=trace_route_stage,
        clock_func=clock_func,
        timestamp_func=timestamp_func,
        safe_str_func=safe_str_func,
    )
