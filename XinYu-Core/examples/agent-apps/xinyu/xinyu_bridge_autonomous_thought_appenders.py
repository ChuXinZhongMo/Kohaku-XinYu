from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_autonomous_thought_payloads import (
    autonomous_outward_kwargs,
    learning_closed_loop_self_thought_kwargs,
    proactive_request_kwargs,
    self_exploration_kwargs,
    self_thought_loop_kwargs,
)
from xinyu_bridge_autonomous_note_responses import (
    autonomous_outward_summary,
    bounded_closed_loop_notes,
    proactive_request_summary,
    self_exploration_summary,
    self_thought_summary,
)
from xinyu_bridge_autonomous_trace_helpers import append_autonomous_error


def append_self_thought_loop_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_self_thought_loop_func: Callable[..., dict[str, Any]],
) -> dict[str, Any] | None:
    try:
        thought = run_self_thought_loop_func(
            runtime.xinyu_dir,
            **self_thought_loop_kwargs(runtime, checked_at=checked_at),
        )
        notes.append(self_thought_summary(thought))
        return thought
    except Exception as exc:
        append_autonomous_error(runtime, notes, "self_thought", exc)
        return None


def append_proactive_request_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_proactive_request_loop_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    try:
        request = run_proactive_request_loop_func(
            runtime.xinyu_dir,
            **proactive_request_kwargs(checked_at=checked_at),
        )
        notes.append(proactive_request_summary(request))
        return request
    except Exception as exc:
        append_autonomous_error(runtime, notes, "proactive_request", exc)
        return {}


def append_self_exploration_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_autonomous_self_exploration_tick_func: Callable[..., dict[str, Any]],
) -> None:
    try:
        exploration = run_autonomous_self_exploration_tick_func(
            runtime.xinyu_dir,
            **self_exploration_kwargs(checked_at=checked_at),
        )
        notes.append(self_exploration_summary(exploration))
    except Exception as exc:
        append_autonomous_error(runtime, notes, "self_exploration", exc)


def append_learning_closed_loop_self_thought_note(
    runtime: Any,
    notes: list[str],
    *,
    thought: dict[str, Any],
    checked_at: str,
    request: dict[str, Any] | None = None,
    timestamp_or_now_iso_func: Callable[..., str],
    record_learning_closed_loop_self_thought_func: Callable[..., dict[str, Any]],
) -> None:
    try:
        kwargs = learning_closed_loop_self_thought_kwargs(
            thought=thought,
            checked_at=checked_at,
            request=request,
            timestamp_or_now_iso_func=timestamp_or_now_iso_func,
        )
        closed_loop = record_learning_closed_loop_self_thought_func(runtime.xinyu_dir, **kwargs)
        notes.extend(bounded_closed_loop_notes(closed_loop))
    except Exception as exc:
        append_autonomous_error(runtime, notes, "learning_closed_loop_self_thought", exc, trace=False)


def append_autonomous_outward_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    prepare_request: bool,
    run_autonomous_outward_action_tick_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    try:
        auto_outward = run_autonomous_outward_action_tick_func(
            runtime.xinyu_dir,
            **autonomous_outward_kwargs(runtime, checked_at=checked_at, prepare_request=prepare_request),
        )
        notes.append(autonomous_outward_summary(auto_outward))
        return auto_outward
    except Exception as exc:
        append_autonomous_error(runtime, notes, "autonomous_outward", exc)
        return {}

