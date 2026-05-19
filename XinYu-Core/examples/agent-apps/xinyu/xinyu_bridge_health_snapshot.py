from __future__ import annotations

from typing import Any

from xinyu_action_experience_digest import read_recent_action_digest_snapshot
from xinyu_code_awareness import record_code_awareness
from xinyu_runtime_presence import DEFAULT_RUNNING_STALE_SECONDS, read_runtime_presence_summary
from xinyu_turn_route_trace import read_turn_route_summary


def metabolism_health(runtime: Any) -> dict[str, Any]:
    task = runtime._metabolism_task
    return {
        "task_running": bool(task is not None and not task.done()),
        "in_progress": runtime._metabolism_in_progress,
        "interval_seconds": runtime.metabolism_runner_interval_seconds,
        "run_count": runtime._metabolism_run_count,
        "last_started_at": runtime._metabolism_last_started_at,
        "last_success_at": runtime._metabolism_last_success_at,
        "last_error": runtime._metabolism_last_error,
    }


def autonomous_maintenance_health(runtime: Any) -> dict[str, Any]:
    task = runtime._autonomous_task
    task_running = bool(task is not None and not task.done())
    task_done = bool(task is not None and task.done())
    return {
        "enabled": runtime.autonomous_maintenance_enabled,
        "task_running": task_running,
        "task_done": task_done,
        "in_progress": runtime._autonomous_in_progress,
        "session_key": runtime.autonomous_maintenance_session_key,
        "initial_delay_seconds": runtime.autonomous_maintenance_initial_delay_seconds,
        "interval_seconds": runtime.autonomous_maintenance_interval_seconds,
        "run_count": runtime._autonomous_run_count,
        "failure_count": runtime._autonomous_failure_count,
        "last_started_at": runtime._autonomous_last_started_at,
        "last_success_at": runtime._autonomous_last_success_at,
        "last_error": runtime._autonomous_last_error,
        "last_memory_changed": runtime._autonomous_last_memory_changed,
        "next_run_at": runtime._autonomous_next_run_at,
    }


def health_snapshot(
    runtime: Any,
    *,
    bridge_version: str,
    source_digest: str,
    runtime_source_digest: str,
) -> dict[str, Any]:
    code_awareness = record_code_awareness(
        runtime.xinyu_dir,
        running_bridge_digest=source_digest,
        running_runtime_digest=runtime_source_digest,
    )
    runtime_presence = read_runtime_presence_summary(runtime.xinyu_dir)
    turn_route = read_turn_route_summary(runtime.xinyu_dir)
    return {
        "ok": True,
        "bridge": "xinyu_core_bridge",
        "version": bridge_version,
        "source_digest": source_digest,
        "runtime_source_digest": runtime_source_digest,
        "xinyu_dir": str(runtime.xinyu_dir),
        "memory_root": str(runtime.memory_root),
        "sessions": len(runtime._sessions),
        "turn_timeout_seconds": runtime.turn_timeout_seconds,
        "pre_model_routes_timeout_seconds": runtime.pre_model_routes_timeout_seconds,
        "outward_renderer": runtime.outward_renderer,
        "renderer_mode": runtime.renderer_mode,
        "render_timeout_seconds": runtime.render_timeout_seconds,
        "session_idle_ttl_seconds": runtime.session_idle_ttl_seconds,
        "max_sessions": runtime.max_sessions,
        "dialogue_memory": {
            "prompt_tail_entries": runtime.dialogue_prompt_tail_entries,
            "session_tail_entries": runtime.dialogue_session_tail_entries,
            "persisted_tail_entries": runtime.dialogue_persisted_tail_entries,
        },
        "proactive_min_interval_seconds": runtime.proactive_min_interval_seconds,
        "autonomous_maintenance": autonomous_maintenance_health(runtime),
        "runtime_presence": runtime_presence,
        "turn_route": turn_route,
        "operator": _operator_health(runtime_presence=runtime_presence, turn_route=turn_route),
        "program_awareness": runtime_presence.get("program_awareness", {}),
        "code_awareness": code_awareness,
        "v1": runtime._v1_health(),
        "metabolism": metabolism_health(runtime),
        "self_choice": runtime.self_choice_store.health_snapshot(),
        "action_experience_digest": read_recent_action_digest_snapshot(runtime.xinyu_dir, limit=3),
        "closed": runtime._closed,
    }


def _operator_health(*, runtime_presence: dict[str, Any], turn_route: dict[str, Any]) -> dict[str, Any]:
    current_turn_age_seconds = _safe_int(runtime_presence.get("current_turn_age_seconds"), 0)
    stale_running = bool(runtime_presence.get("stale_running"))
    stale_age_seconds = 0
    if stale_running and current_turn_age_seconds > DEFAULT_RUNNING_STALE_SECONDS:
        stale_age_seconds = current_turn_age_seconds - DEFAULT_RUNNING_STALE_SECONDS
    return {
        "current_turn_state": _safe_str(runtime_presence.get("current_turn_state"), "unknown"),
        "current_turn_age_seconds": current_turn_age_seconds,
        "route_stage": _safe_str(turn_route.get("last_stage"), "unknown"),
        "route": _safe_str(turn_route.get("last_route"), "unknown"),
        "route_status": _safe_str(turn_route.get("last_status"), "unknown"),
        "stale_running": stale_running,
        "stale_age_seconds": stale_age_seconds,
        "last_timeout_stage": _safe_str(turn_route.get("last_timeout_stage")),
        "last_timeout_reason": _safe_str(turn_route.get("last_timeout_reason")),
    }


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
