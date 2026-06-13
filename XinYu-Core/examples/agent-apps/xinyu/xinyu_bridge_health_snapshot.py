from __future__ import annotations

from typing import Any

from xinyu_action_experience_digest import read_recent_action_digest_snapshot
from xinyu_bridge_health_diagnostics_service import (
    HealthDiagnosticsDeps,
    build_health_diagnostics_service,
)
from xinyu_bridge_health_provider_registry import health_diagnostics_provider_registry_providers
from xinyu_bridge_health_snapshot_service import build_operator_health
from xinyu_code_awareness import read_code_awareness_summary
from xinyu_runtime_presence import read_runtime_presence_summary
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
    service = getattr(runtime, "_health_diagnostics_service", None)
    if service is None:
        service = build_runtime_health_diagnostics_service()
    return service.health_snapshot(
        runtime,
        bridge_version=bridge_version,
        source_digest=source_digest,
        runtime_source_digest=runtime_source_digest,
    )


def build_runtime_health_diagnostics_service():
    return build_health_diagnostics_service(
        HealthDiagnosticsDeps(
            read_code_awareness_summary_func=read_code_awareness_summary,
            read_runtime_presence_summary_func=read_runtime_presence_summary,
            read_turn_route_summary_func=read_turn_route_summary,
            read_recent_action_digest_snapshot_func=read_recent_action_digest_snapshot,
            autonomous_maintenance_health_func=autonomous_maintenance_health,
            metabolism_health_func=metabolism_health,
            operator_health_func=build_operator_health,
            service_health_providers_func=health_diagnostics_provider_registry_providers,
        )
    )


def runtime_health_snapshot(runtime: Any) -> dict[str, Any]:
    return health_snapshot(
        runtime,
        bridge_version=_safe_str(getattr(runtime, "bridge_version", ""), "unknown"),
        source_digest=_safe_str(getattr(runtime, "bridge_source_digest", "")),
        runtime_source_digest=_safe_str(getattr(runtime, "bridge_runtime_source_digest", "")),
    )


async def runtime_health(runtime: Any) -> dict[str, Any]:
    return runtime_health_snapshot(runtime)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default
