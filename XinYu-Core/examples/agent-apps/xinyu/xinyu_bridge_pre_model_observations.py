from __future__ import annotations

from collections.abc import Callable
from typing import Any


TraceRouteStage = Callable[..., Any]


def run_pre_model_observation_sidecars_with_trace(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    trace_route_stage: TraceRouteStage,
    observed_at: str | None = None,
    curiosity_func: Callable[..., dict[str, Any]],
    private_thought_func: Callable[..., dict[str, Any]],
    uncertainty_pause_func: Callable[..., dict[str, Any]],
    observed_at_func: Callable[[], str],
) -> dict[str, dict[str, Any]]:
    curiosity_eval: dict[str, Any] = {"notes": []}
    try:
        trace_route_stage("curiosity_eval_started")
        curiosity_eval = curiosity_func(
            runtime.xinyu_dir,
            payload,
            text=text,
            session_key=session_key,
        )
        trace_route_stage("curiosity_eval_finished", status="ok")
    except Exception as exc:
        print(f"[xinyu_core_bridge] dialogue curiosity evaluation failed: {exc}", flush=True)
        curiosity_eval = {"notes": [f"dialogue_curiosity_eval_error:{type(exc).__name__}"]}
        trace_route_stage(
            "curiosity_eval_finished",
            status="error",
            notes=[f"dialogue_curiosity_eval_error:{type(exc).__name__}"],
        )

    private_thought_outcome: dict[str, Any] = {"notes": []}
    try:
        trace_route_stage("private_thought_outcome_started")
        private_thought_outcome = private_thought_func(
            runtime.xinyu_dir,
            payload,
            text=text,
            session_key=session_key,
            evaluation=curiosity_eval,
        )
        trace_route_stage("private_thought_outcome_finished", status="ok")
    except Exception as exc:
        print(f"[xinyu_core_bridge] private thought outcome failed: {exc}", flush=True)
        private_thought_outcome = {"notes": [f"private_thought_outcome_error:{type(exc).__name__}"]}
        trace_route_stage(
            "private_thought_outcome_finished",
            status="error",
            notes=[f"private_thought_outcome_error:{type(exc).__name__}"],
        )

    uncertainty_pause_reply: dict[str, Any] = {"notes": []}
    try:
        trace_route_stage("uncertainty_pause_mark_started")
        uncertainty_pause_reply = uncertainty_pause_func(
            runtime.xinyu_dir,
            text=text,
            observed_at=observed_at or observed_at_func(),
        )
        trace_route_stage("uncertainty_pause_mark_finished", status="ok")
    except Exception as exc:
        print(f"[xinyu_core_bridge] uncertainty pause reply mark failed: {exc}", flush=True)
        uncertainty_pause_reply = {"notes": [f"uncertainty_pause_reply_error:{type(exc).__name__}"]}
        trace_route_stage(
            "uncertainty_pause_mark_finished",
            status="error",
            notes=[f"uncertainty_pause_reply_error:{type(exc).__name__}"],
        )

    return {
        "curiosity_eval": curiosity_eval,
        "private_thought_outcome": private_thought_outcome,
        "uncertainty_pause_reply": uncertainty_pause_reply,
    }
