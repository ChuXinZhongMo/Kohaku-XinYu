from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_stores import append_autonomous_trace_text


def trace_autonomous(runtime: Any, line: str, *, now_iso_func: Callable[[], str]) -> None:
    trace_path = runtime.memory_root / "context/autonomous_mind_loop_trace.log"
    append_autonomous_trace_text(trace_path, f"{now_iso_func()} {line}\n")


def write_autonomous_state(
    runtime: Any,
    status: str,
    *,
    memory_changed: bool | None,
    notes: list[str] | None,
    now_iso_func: Callable[[], str],
    atomic_write_text_func: Callable[..., None],
) -> None:
    state_path = runtime.memory_root / "context/autonomous_mind_loop_state.md"
    updated_at = now_iso_func()
    if notes is not None:
        runtime._autonomous_last_notes = notes
    if memory_changed is not None:
        runtime._autonomous_last_memory_changed = str(memory_changed).lower()
    note_lines = "\n".join(f"- {note}" for note in runtime._autonomous_last_notes) or "- none"
    text = f"""---
title: Autonomous Mind Loop State
memory_type: autonomous_mind_loop_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_core_bridge
updated_at: {updated_at}
status: active
tags: [autonomy, maintenance, runtime]
---

# Autonomous Mind Loop State

## Runtime
- status: {status}
- enabled: {str(runtime.autonomous_maintenance_enabled).lower()}
- in_progress: {str(runtime._autonomous_in_progress).lower()}
- session_key: {runtime.autonomous_maintenance_session_key}
- initial_delay_seconds: {runtime.autonomous_maintenance_initial_delay_seconds}
- interval_seconds: {runtime.autonomous_maintenance_interval_seconds}
- next_run_at: {runtime._autonomous_next_run_at or "unknown"}

## Last Run
- run_count: {runtime._autonomous_run_count}
- failure_count: {runtime._autonomous_failure_count}
- last_started_at: {runtime._autonomous_last_started_at or "never"}
- last_success_at: {runtime._autonomous_last_success_at or "never"}
- memory_changed: {runtime._autonomous_last_memory_changed}
- last_error: {runtime._autonomous_last_error or "none"}

## Notes
{note_lines}
"""
    try:
        atomic_write_text_func(state_path, text)
    except Exception:
        pass
