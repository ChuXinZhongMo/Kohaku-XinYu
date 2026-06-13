from __future__ import annotations

import asyncio
from typing import Any

from xinyu_bridge_session import stop_all_sessions


async def ensure_self_choice_ready(runtime: Any) -> None:
    await runtime.self_choice_store.load_or_recover()


def start_state_persistence_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_state_persistence_service", None)
    if handle is None:
        return None
    return handle.start(runtime)


def stop_state_persistence_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_state_persistence_service", None)
    if handle is None:
        return None
    return handle.close(runtime)


def start_chat_turn_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_chat_turn_service", None)
    if handle is None:
        return None
    return handle.start(runtime)


def stop_chat_turn_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_chat_turn_service", None)
    if handle is None:
        return None
    return handle.close(runtime)


def start_codex_execution_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_codex_execution_service", None)
    if handle is None:
        return None
    return handle.start(runtime)


def stop_codex_execution_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_codex_execution_service", None)
    if handle is None:
        return None
    return handle.close(runtime)


def start_external_action_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_external_action_service", None)
    if handle is None:
        return None
    return handle.start(runtime)


def stop_external_action_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_external_action_service", None)
    if handle is None:
        return None
    return handle.close(runtime)


def start_desktop_surface_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_desktop_surface_service", None)
    if handle is None:
        return None
    return handle.start(runtime)


def stop_desktop_surface_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_desktop_surface_service", None)
    if handle is None:
        return None
    return handle.close(runtime)


def start_proactive_delivery_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_proactive_delivery_service", None)
    if handle is None:
        return None
    return handle.start(runtime)


def stop_proactive_delivery_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_proactive_delivery_service", None)
    if handle is None:
        return None
    return handle.close(runtime)


def start_life_metabolism_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_life_metabolism_service", None)
    if handle is None:
        return None
    return handle.start(runtime)


def stop_life_metabolism_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_life_metabolism_service", None)
    if handle is None:
        return None
    return handle.close(runtime)


def start_learning_ingest_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_learning_ingest_service", None)
    if handle is None:
        return None
    return handle.start(runtime)


def stop_learning_ingest_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_learning_ingest_service", None)
    if handle is None:
        return None
    return handle.close(runtime)


def start_diagnostic_reports_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_diagnostic_reports_service", None)
    if handle is None:
        return None
    return handle.start(runtime)


def stop_diagnostic_reports_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_diagnostic_reports_service", None)
    if handle is None:
        return None
    return handle.close(runtime)


def start_memory_governance_reports_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_memory_governance_reports_service", None)
    if handle is None:
        return None
    return handle.start(runtime)


def stop_memory_governance_reports_service(runtime: Any) -> Any:
    handle = getattr(runtime, "_memory_governance_reports_service", None)
    if handle is None:
        return None
    return handle.close(runtime)


def start_health_diagnostics_service(runtime: Any) -> Any:
    service = getattr(runtime, "_health_diagnostics_service", None)
    if service is None:
        return None
    start = getattr(service, "start", None)
    if callable(start):
        return start()
    return None


def stop_health_diagnostics_service(runtime: Any) -> Any:
    service = getattr(runtime, "_health_diagnostics_service", None)
    if service is None:
        return None
    stop = getattr(service, "stop", None)
    if callable(stop):
        return stop()
    return None


RUNTIME_SERVICE_STARTERS = (
    "start_state_persistence_service",
    "start_chat_turn_service",
    "start_codex_execution_service",
    "start_external_action_service",
    "start_desktop_surface_service",
    "start_proactive_delivery_service",
    "start_life_metabolism_service",
    "start_learning_ingest_service",
    "start_diagnostic_reports_service",
    "start_memory_governance_reports_service",
    "start_health_diagnostics_service",
)

RUNTIME_SERVICE_STOPPERS = (
    ("stop_chat_turn_service", "chat turn"),
    ("stop_codex_execution_service", "codex execution"),
    ("stop_external_action_service", "external action"),
    ("stop_desktop_surface_service", "desktop surface"),
    ("stop_proactive_delivery_service", "proactive delivery"),
    ("stop_life_metabolism_service", "life metabolism"),
    ("stop_learning_ingest_service", "learning ingest"),
    ("stop_diagnostic_reports_service", "diagnostic reports"),
    ("stop_memory_governance_reports_service", "memory governance reports"),
    ("stop_health_diagnostics_service", "health diagnostics"),
    ("stop_state_persistence_service", "state persistence"),
)


def _call_lifecycle_function(name: str, runtime: Any) -> Any:
    return globals()[name](runtime)


def _stop_runtime_service(runtime: Any, stopper_name: str, label: str) -> None:
    try:
        _call_lifecycle_function(stopper_name, runtime)
    except Exception as exc:
        print(f"[xinyu_core_bridge] {label} service shutdown warning: {exc}", flush=True)


async def start_background_tasks(runtime: Any) -> None:
    if runtime._closed:
        return
    for starter_name in RUNTIME_SERVICE_STARTERS:
        _call_lifecycle_function(starter_name, runtime)
    await runtime._ensure_self_choice_ready()
    await runtime.self_choice_store.apply_time_decay()
    if not runtime._self_choice_boot_logged:
        print(runtime.self_choice_store.boot_log_line(), flush=True)
        runtime._self_choice_boot_logged = True
    if runtime._metabolism_wakeup_event is None:
        runtime._metabolism_wakeup_event = asyncio.Event()
    if runtime._metabolism_task is None or runtime._metabolism_task.done():
        runtime._metabolism_task = asyncio.create_task(
            runtime._metabolism_runner_loop(),
            name="xinyu-metabolism-runner",
        )
    if not runtime.autonomous_maintenance_enabled:
        runtime._trace_autonomous("background disabled")
        runtime._write_autonomous_state("disabled")
        return
    if runtime._autonomous_task is not None and not runtime._autonomous_task.done():
        return
    runtime._autonomous_task = asyncio.create_task(
        runtime._autonomous_maintenance_loop(),
        name="xinyu-autonomous-maintenance",
    )
    runtime._trace_autonomous("background task started")
    runtime._write_autonomous_state("starting")


async def shutdown(runtime: Any) -> None:
    runtime._closed = True
    for stopper_name, label in RUNTIME_SERVICE_STOPPERS:
        _stop_runtime_service(runtime, stopper_name, label)

    metabolism_task = runtime._metabolism_task
    runtime._metabolism_task = None
    if runtime._metabolism_wakeup_event is not None:
        runtime._metabolism_wakeup_event.set()
    if metabolism_task is not None and not metabolism_task.done():
        metabolism_task.cancel()
        try:
            await metabolism_task
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            print(f"[xinyu_core_bridge] metabolism task shutdown warning: {exc}", flush=True)

    autonomous_task = runtime._autonomous_task
    runtime._autonomous_task = None
    if autonomous_task is not None and not autonomous_task.done():
        autonomous_task.cancel()
        try:
            await autonomous_task
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            print(f"[xinyu_core_bridge] autonomous task shutdown warning: {exc}", flush=True)

    try:
        await runtime.self_choice_store.shutdown()
    except Exception as exc:
        print(f"[xinyu_core_bridge] self choice shutdown warning: {exc}", flush=True)

    try:
        runtime.tts_output.close()
    except Exception as exc:
        print(f"[xinyu_core_bridge] tts shutdown warning: {exc}", flush=True)

    await stop_all_sessions(runtime._sessions, runtime._sessions_lock)
