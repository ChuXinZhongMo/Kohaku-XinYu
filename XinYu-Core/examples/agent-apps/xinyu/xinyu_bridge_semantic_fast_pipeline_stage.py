from __future__ import annotations

from collections.abc import Callable
from typing import Any


TraceRouteStage = Callable[..., Any]
SEMANTIC_FAST_ROUTE = "owner_private_semantic_fast"
SLOW_LIVE_ROUTE = "slow_live"


def semantic_fast_note_preview(
    decision: dict[str, Any],
    *,
    safe_str_func: Callable[..., str],
    limit: int = 4,
) -> list[str]:
    return [safe_str_func(note) for note in decision.get("notes", [])[:limit]]


def trace_semantic_fast_probe_started(trace_route_stage: TraceRouteStage) -> None:
    trace_route_stage("semantic_fast_probe_started")


def trace_semantic_fast_probe_finished(
    trace_route_stage: TraceRouteStage,
    decision: dict[str, Any],
    *,
    safe_str_func: Callable[..., str],
) -> None:
    trace_route_stage(
        "semantic_fast_probe_finished",
        status="allowed" if decision.get("allowed") else "skipped",
        notes=semantic_fast_note_preview(decision, safe_str_func=safe_str_func),
    )


def trace_semantic_fast_probe_error(trace_route_stage: TraceRouteStage, error_note: str) -> None:
    trace_route_stage(
        "semantic_fast_probe_finished",
        status="error",
        notes=[error_note],
    )


def trace_semantic_fast_route_decided(
    trace_route_stage: TraceRouteStage,
    decision: dict[str, Any],
    *,
    safe_str_func: Callable[..., str],
) -> None:
    trace_route_stage(
        "route_decided",
        route=SEMANTIC_FAST_ROUTE,
        status="accepted",
        notes=semantic_fast_note_preview(decision, safe_str_func=safe_str_func),
    )


def trace_slow_live_route_after_semantic_fast(trace_route_stage: TraceRouteStage) -> None:
    trace_route_stage(
        "route_decided",
        route=SLOW_LIVE_ROUTE,
        status="accepted",
        notes=["semantic_fast_not_intercepted"],
    )


def trace_semantic_fast_direct_started(trace_route_stage: TraceRouteStage) -> None:
    trace_route_stage("semantic_fast_direct_started", route=SEMANTIC_FAST_ROUTE)


def trace_semantic_fast_direct_finished_empty(trace_route_stage: TraceRouteStage) -> None:
    trace_route_stage(
        "semantic_fast_direct_finished",
        route=SEMANTIC_FAST_ROUTE,
        status="empty_or_blocked",
    )


def trace_semantic_fast_session_started(trace_route_stage: TraceRouteStage) -> None:
    trace_route_stage("semantic_fast_session_started", route=SEMANTIC_FAST_ROUTE)


def trace_semantic_fast_session_finished(trace_route_stage: TraceRouteStage) -> None:
    trace_route_stage("semantic_fast_session_finished", route=SEMANTIC_FAST_ROUTE, status="ok")


def trace_semantic_fast_fell_through_empty(trace_route_stage: TraceRouteStage) -> None:
    trace_route_stage(
        "semantic_fast_fell_through",
        route=SEMANTIC_FAST_ROUTE,
        status="empty_or_blocked",
    )


def trace_semantic_fast_fell_through_error(trace_route_stage: TraceRouteStage, error_note: str) -> None:
    trace_route_stage(
        "semantic_fast_fell_through",
        route=SEMANTIC_FAST_ROUTE,
        status="error",
        notes=[error_note],
    )
