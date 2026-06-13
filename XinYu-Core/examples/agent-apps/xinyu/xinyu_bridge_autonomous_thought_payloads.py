from __future__ import annotations

from typing import Any, Callable


def self_thought_loop_kwargs(runtime: Any, *, checked_at: str) -> dict[str, Any]:
    return {
        "checked_at": checked_at,
        "trigger": "autonomous_maintenance",
        "min_interval_seconds": runtime.autonomous_maintenance_interval_seconds,
    }


def proactive_request_kwargs(*, checked_at: str) -> dict[str, Any]:
    return {
        "evaluated_at": checked_at,
        "delivery_level": "queue_owner_private",
    }


def self_exploration_kwargs(*, checked_at: str) -> dict[str, Any]:
    return {
        "evaluated_at": checked_at,
        "allow_live_search": None,
        "allow_codex": None,
        "execute_low_risk": False,
    }


def learning_closed_loop_self_thought_kwargs(
    *,
    thought: dict[str, Any],
    checked_at: str,
    request: dict[str, Any] | None,
    timestamp_or_now_iso_func: Callable[..., str],
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "thought": thought,
        "observed_at": timestamp_or_now_iso_func(checked_at),
    }
    if request is not None:
        kwargs["request"] = request
    return kwargs


def autonomous_outward_kwargs(
    runtime: Any,
    *,
    checked_at: str,
    prepare_request: bool,
) -> dict[str, Any]:
    return {
        "evaluated_at": checked_at,
        "min_interval_seconds": max(1800, runtime.autonomous_maintenance_interval_seconds),
        "max_messages_per_day": 3,
        "dry_run": False,
        "prepare_request": prepare_request,
    }
