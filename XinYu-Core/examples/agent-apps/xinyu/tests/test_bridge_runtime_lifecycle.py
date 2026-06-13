from __future__ import annotations

import asyncio
from dataclasses import fields
from types import SimpleNamespace

from xinyu_bridge_codex_execution_backend import (
    CODEX_EXECUTION_BACKEND_RUNTIME_ATTR,
    CODEX_EXECUTION_IN_PROCESS_BACKEND,
    codex_execution_backend_for_runtime,
)
from xinyu_bridge_chat_turn_service import build_chat_turn_service_handle
from xinyu_bridge_codex_execution_service import (
    CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT,
    CodexExecutionServiceConfig,
    build_codex_execution_service_handle,
)
from xinyu_bridge_codex_execution_worker_client import CODEX_EXECUTION_WORKER_CLIENT_MODE
from xinyu_bridge_external_action_backend import (
    EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE,
    EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR,
    external_action_backend_for_runtime,
)
from xinyu_bridge_external_action_service import (
    EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN,
    ExternalActionServiceConfig,
    build_external_action_service_handle,
)
from xinyu_bridge_desktop_surface_route_backend import (
    DESKTOP_SURFACE_BACKEND_DRY_RUN_MODE,
    DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR,
    desktop_surface_route_backend_for_runtime,
)
from xinyu_bridge_desktop_surface_service import (
    DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
    DesktopSurfaceServiceConfig,
    build_desktop_surface_service_handle,
)
from xinyu_bridge_proactive_delivery_route_backend import (
    PROACTIVE_DELIVERY_BACKEND_DRY_RUN_MODE,
    PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR,
    proactive_delivery_route_backend_for_runtime,
)
from xinyu_bridge_proactive_delivery_service import (
    PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
    ProactiveDeliveryServiceConfig,
    build_proactive_delivery_service_handle,
)
from xinyu_bridge_life_metabolism_route_backend import (
    LIFE_METABOLISM_BACKEND_DRY_RUN_MODE,
    LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR,
    life_metabolism_route_backend_for_runtime,
)
from xinyu_bridge_life_metabolism_service import (
    LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
    LifeMetabolismServiceConfig,
    build_life_metabolism_service_handle,
)
from xinyu_bridge_learning_ingest_route_backend import (
    LEARNING_INGEST_BACKEND_DRY_RUN_MODE,
    LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR,
    learning_ingest_route_backend_for_runtime,
)
from xinyu_bridge_learning_ingest_service import (
    LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
    LearningIngestServiceConfig,
    build_learning_ingest_service_handle,
)
from xinyu_bridge_local_report_services import (
    build_diagnostic_reports_service_handle,
    build_memory_governance_reports_service_handle,
)
from xinyu_bridge_state_persistence_service import build_state_persistence_service_handle
from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY as CONTRACT_DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY,
    DESKTOP_EVENT_STREAM_RUNTIME_ATTR as CONTRACT_DESKTOP_EVENT_STREAM_RUNTIME_ATTR,
)
from xinyu_bridge_runtime_state_service_bindings import RuntimeServiceBindings
from xinyu_desktop_service import DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY, DESKTOP_EVENT_STREAM_RUNTIME_ATTR
import xinyu_bridge_runtime_lifecycle


class _Task:
    def __init__(self, done: bool = False) -> None:
        self._done = done

    def done(self) -> bool:
        return self._done


def test_ensure_self_choice_ready_loads_store() -> None:
    calls: list[str] = []

    class _Store:
        async def load_or_recover(self) -> None:
            calls.append("load")

    asyncio.run(xinyu_bridge_runtime_lifecycle.ensure_self_choice_ready(SimpleNamespace(self_choice_store=_Store())))

    assert calls == ["load"]


def test_runtime_service_lifecycle_order_contract() -> None:
    assert xinyu_bridge_runtime_lifecycle.RUNTIME_SERVICE_STARTERS == (
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
    assert xinyu_bridge_runtime_lifecycle.RUNTIME_SERVICE_STOPPERS == (
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


def test_runtime_service_bindings_have_lifecycle_start_stop_coverage() -> None:
    binding_services = {
        field.name.removeprefix("build_")
        for field in fields(RuntimeServiceBindings)
        if field.name.startswith("build_")
        and field.name.endswith("_service")
        and field.name not in {"build_chat_service", "build_learning_service"}
    }
    starter_services = {
        name.removeprefix("start_")
        for name in xinyu_bridge_runtime_lifecycle.RUNTIME_SERVICE_STARTERS
    }
    stopper_services = {
        name.removeprefix("stop_")
        for name, _label in xinyu_bridge_runtime_lifecycle.RUNTIME_SERVICE_STOPPERS
    }

    assert binding_services == starter_services
    assert binding_services == stopper_services


def test_desktop_event_stream_lifecycle_remains_app_owned() -> None:
    binding_names = {field.name for field in fields(RuntimeServiceBindings)}
    starter_names = set(xinyu_bridge_runtime_lifecycle.RUNTIME_SERVICE_STARTERS)
    stopper_names = {name for name, _label in xinyu_bridge_runtime_lifecycle.RUNTIME_SERVICE_STOPPERS}

    assert DESKTOP_EVENT_STREAM_RUNTIME_ATTR == "_desktop_event_stream_service"
    assert DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY == "app_owned_websocket_lifecycle_not_runtime_service_starter"
    assert DESKTOP_EVENT_STREAM_RUNTIME_ATTR == CONTRACT_DESKTOP_EVENT_STREAM_RUNTIME_ATTR
    assert DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY == CONTRACT_DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY
    assert "build_desktop_event_stream_service" not in binding_names
    assert "start_desktop_event_stream_service" not in starter_names
    assert "stop_desktop_event_stream_service" not in stopper_names


def test_start_background_tasks_starts_metabolism_and_records_disabled_autonomy(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Store:
        async def apply_time_decay(self) -> None:
            calls.append(("store", "decay"))

        def boot_log_line(self) -> str:
            calls.append(("store", "boot_log"))
            return "boot"

    async def ensure_ready() -> None:
        calls.append(("ensure", "self_choice"))

    async def metabolism_loop() -> None:
        calls.append(("metabolism", "body"))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return _Task(done=False)

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "Event", lambda: "event")
    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "create_task", fake_create_task)
    runtime = SimpleNamespace(
        _closed=False,
        _ensure_self_choice_ready=ensure_ready,
        self_choice_store=_Store(),
        _self_choice_boot_logged=False,
        _metabolism_wakeup_event=None,
        _metabolism_task=None,
        _metabolism_runner_loop=metabolism_loop,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_maintenance_loop=lambda: None,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.start_background_tasks(runtime))

    assert runtime._self_choice_boot_logged is True
    assert runtime._metabolism_wakeup_event == "event"
    assert isinstance(runtime._metabolism_task, _Task)
    assert runtime._autonomous_task is None
    assert calls == [
        ("ensure", "self_choice"),
        ("store", "decay"),
        ("store", "boot_log"),
        ("task", "xinyu-metabolism-runner"),
        ("trace", "background disabled"),
        ("state", "disabled"),
    ]


def test_start_background_tasks_starts_autonomous_when_needed(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Store:
        async def apply_time_decay(self) -> None:
            calls.append(("store", "decay"))

    async def ensure_ready() -> None:
        calls.append(("ensure", "self_choice"))

    async def metabolism_loop() -> None:
        calls.append(("metabolism", "body"))

    async def autonomous_loop() -> None:
        calls.append(("autonomous", "body"))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return _Task(done=False)

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "create_task", fake_create_task)
    runtime = SimpleNamespace(
        _closed=False,
        _ensure_self_choice_ready=ensure_ready,
        self_choice_store=_Store(),
        _self_choice_boot_logged=True,
        _metabolism_wakeup_event="event",
        _metabolism_task=_Task(done=False),
        _metabolism_runner_loop=metabolism_loop,
        autonomous_maintenance_enabled=True,
        _autonomous_task=None,
        _autonomous_maintenance_loop=autonomous_loop,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.start_background_tasks(runtime))

    assert isinstance(runtime._autonomous_task, _Task)
    assert calls == [
        ("ensure", "self_choice"),
        ("store", "decay"),
        ("task", "xinyu-autonomous-maintenance"),
        ("trace", "background task started"),
        ("state", "starting"),
    ]


def test_start_background_tasks_starts_codex_execution_service(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Store:
        async def apply_time_decay(self) -> None:
            calls.append(("store", "decay"))

    class _CodexService:
        def start(self, runtime) -> dict[str, object]:
            calls.append(("codex", runtime._closed))
            return {"ready": True}

    async def ensure_ready() -> None:
        calls.append(("ensure", "self_choice"))

    async def metabolism_loop() -> None:
        calls.append(("metabolism", "body"))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return _Task(done=False)

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "create_task", fake_create_task)
    runtime = SimpleNamespace(
        _closed=False,
        _codex_execution_service=_CodexService(),
        _ensure_self_choice_ready=ensure_ready,
        self_choice_store=_Store(),
        _self_choice_boot_logged=True,
        _metabolism_wakeup_event="event",
        _metabolism_task=None,
        _metabolism_runner_loop=metabolism_loop,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_maintenance_loop=lambda: None,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.start_background_tasks(runtime))

    assert calls == [
        ("codex", False),
        ("ensure", "self_choice"),
        ("store", "decay"),
        ("task", "xinyu-metabolism-runner"),
        ("trace", "background disabled"),
        ("state", "disabled"),
    ]


def test_chat_turn_service_lifecycle_starts_before_background_work_and_stops(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Store:
        async def apply_time_decay(self) -> None:
            calls.append(("store", "decay"))

        async def shutdown(self) -> None:
            calls.append(("store", "shutdown"))

    class _TTS:
        def close(self) -> None:
            calls.append(("tts", "close"))

    class _ChatService:
        def prepare_request(self):
            return None

        def start_turn_clock(self):
            return None

    async def ensure_ready() -> None:
        calls.append(("ensure", "self_choice"))

    async def metabolism_loop() -> None:
        calls.append(("metabolism", "body"))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return _Task(done=False)

    async def fake_stop_all_sessions(sessions, lock) -> dict[str, object]:
        calls.append(("sessions", (sessions, lock)))
        return {"stopped": 0}

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle, "stop_all_sessions", fake_stop_all_sessions)
    runtime = SimpleNamespace(
        _closed=False,
        _chat_turn_service=build_chat_turn_service_handle(),
        chat=lambda payload: payload,
        chat_service=_ChatService(),
        _ensure_self_choice_ready=ensure_ready,
        self_choice_store=_Store(),
        tts_output=_TTS(),
        _self_choice_boot_logged=True,
        _metabolism_wakeup_event=None,
        _metabolism_task=None,
        _metabolism_runner_loop=metabolism_loop,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_maintenance_loop=lambda: None,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
        _sessions={},
        _sessions_lock=object(),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.start_background_tasks(runtime))

    assert runtime._chat_turn_service.readiness(runtime).started is True
    assert runtime._chat_turn_service.readiness(runtime).ready is True

    runtime._metabolism_task = None
    asyncio.run(xinyu_bridge_runtime_lifecycle.shutdown(runtime))

    assert runtime._chat_turn_service.readiness(runtime).started is False


def test_state_persistence_service_lifecycle_starts_and_stops(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Store:
        async def apply_time_decay(self) -> None:
            calls.append(("store", "decay"))

        async def shutdown(self) -> None:
            calls.append(("store", "shutdown"))

    class _TTS:
        def close(self) -> None:
            calls.append(("tts", "close"))

    async def ensure_ready() -> None:
        calls.append(("ensure", "self_choice"))

    async def metabolism_loop() -> None:
        calls.append(("metabolism", "body"))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return _Task(done=False)

    async def fake_stop_all_sessions(sessions, lock) -> dict[str, object]:
        calls.append(("sessions", (sessions, lock)))
        return {"stopped": 0}

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle, "stop_all_sessions", fake_stop_all_sessions)
    runtime = SimpleNamespace(
        _closed=False,
        _state_persistence_service=build_state_persistence_service_handle(),
        _ensure_self_choice_ready=ensure_ready,
        self_choice_store=_Store(),
        tts_output=_TTS(),
        _self_choice_boot_logged=True,
        _metabolism_wakeup_event=None,
        _metabolism_task=None,
        _metabolism_runner_loop=metabolism_loop,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_maintenance_loop=lambda: None,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
        _sessions={},
        _sessions_lock=object(),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.start_background_tasks(runtime))

    assert runtime._state_persistence_service.readiness(runtime).started is True
    assert runtime._state_persistence_service.readiness(runtime).ready is True

    runtime._metabolism_task = None
    asyncio.run(xinyu_bridge_runtime_lifecycle.shutdown(runtime))

    assert runtime._state_persistence_service.readiness(runtime).started is False


def test_shutdown_cancels_tasks_and_closes_resources(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Wakeup:
        def set(self) -> None:
            calls.append(("wakeup", "set"))

    class _Store:
        async def shutdown(self) -> None:
            calls.append(("store", "shutdown"))

    class _TTS:
        def close(self) -> None:
            calls.append(("tts", "close"))

    async def sleeper(label: str) -> None:
        try:
            await asyncio.Event().wait()
        finally:
            calls.append(("task_cancelled", label))

    async def fake_stop_all_sessions(sessions, lock) -> dict[str, object]:
        calls.append(("sessions", (sessions, lock)))
        return {"stopped": 1}

    async def run_case() -> SimpleNamespace:
        runtime = SimpleNamespace(
            _closed=False,
            _metabolism_task=asyncio.create_task(sleeper("metabolism")),
            _metabolism_wakeup_event=_Wakeup(),
            _autonomous_task=asyncio.create_task(sleeper("autonomous")),
            self_choice_store=_Store(),
            tts_output=_TTS(),
            _sessions={"a": object()},
            _sessions_lock=object(),
        )
        await asyncio.sleep(0)
        await xinyu_bridge_runtime_lifecycle.shutdown(runtime)
        return runtime

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle, "stop_all_sessions", fake_stop_all_sessions)

    runtime = asyncio.run(run_case())

    assert runtime._closed is True
    assert runtime._metabolism_task is None
    assert runtime._autonomous_task is None
    assert ("wakeup", "set") in calls
    assert ("task_cancelled", "metabolism") in calls
    assert ("task_cancelled", "autonomous") in calls
    assert ("store", "shutdown") in calls
    assert ("tts", "close") in calls
    assert calls[-1][0] == "sessions"


def test_shutdown_closes_codex_execution_service(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _CodexService:
        def close(self, runtime) -> dict[str, object]:
            calls.append(("codex", runtime._closed))
            return {"closed": True}

    class _Store:
        async def shutdown(self) -> None:
            calls.append(("store", "shutdown"))

    class _TTS:
        def close(self) -> None:
            calls.append(("tts", "close"))

    async def fake_stop_all_sessions(sessions, lock) -> dict[str, object]:
        calls.append(("sessions", (sessions, lock)))
        return {"stopped": 0}

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle, "stop_all_sessions", fake_stop_all_sessions)
    runtime = SimpleNamespace(
        _closed=False,
        _codex_execution_service=_CodexService(),
        _metabolism_task=None,
        _metabolism_wakeup_event=None,
        _autonomous_task=None,
        self_choice_store=_Store(),
        tts_output=_TTS(),
        _sessions={},
        _sessions_lock=object(),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.shutdown(runtime))

    assert runtime._closed is True
    assert calls[0] == ("codex", True)
    assert calls[-1][0] == "sessions"


def test_codex_execution_service_lifecycle_injects_and_clears_worker_backend(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Store:
        async def apply_time_decay(self) -> None:
            calls.append(("store", "decay"))

        async def shutdown(self) -> None:
            calls.append(("store", "shutdown"))

    class _TTS:
        def close(self) -> None:
            calls.append(("tts", "close"))

    async def ensure_ready() -> None:
        calls.append(("ensure", "self_choice"))

    async def metabolism_loop() -> None:
        calls.append(("metabolism", "body"))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return _Task(done=False)

    async def fake_stop_all_sessions(sessions, lock) -> dict[str, object]:
        calls.append(("sessions", (sessions, lock)))
        return {"stopped": 0}

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle, "stop_all_sessions", fake_stop_all_sessions)
    runtime = SimpleNamespace(
        _closed=False,
        _codex_execution_service=build_codex_execution_service_handle(
            CodexExecutionServiceConfig(
                mode=CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT,
                worker_enabled=True,
                worker_healthy=True,
            )
        ),
        _ensure_self_choice_ready=ensure_ready,
        self_choice_store=_Store(),
        tts_output=_TTS(),
        _self_choice_boot_logged=True,
        _metabolism_wakeup_event="event",
        _metabolism_task=None,
        _metabolism_runner_loop=metabolism_loop,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_maintenance_loop=lambda: None,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
        _sessions={},
        _sessions_lock=object(),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.start_background_tasks(runtime))

    assert hasattr(runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR)
    assert codex_execution_backend_for_runtime(runtime).mode == CODEX_EXECUTION_WORKER_CLIENT_MODE

    runtime._metabolism_task = None
    runtime._metabolism_wakeup_event = None
    asyncio.run(xinyu_bridge_runtime_lifecycle.shutdown(runtime))

    assert runtime._closed is True
    assert not hasattr(runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR)
    assert codex_execution_backend_for_runtime(runtime).mode == CODEX_EXECUTION_IN_PROCESS_BACKEND


def test_external_action_service_lifecycle_injects_and_clears_dry_run_backend(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Store:
        async def apply_time_decay(self) -> None:
            calls.append(("store", "decay"))

        async def shutdown(self) -> None:
            calls.append(("store", "shutdown"))

    class _TTS:
        def close(self) -> None:
            calls.append(("tts", "close"))

    async def ensure_ready() -> None:
        calls.append(("ensure", "self_choice"))

    async def metabolism_loop() -> None:
        calls.append(("metabolism", "body"))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return _Task(done=False)

    async def fake_stop_all_sessions(sessions, lock) -> dict[str, object]:
        calls.append(("sessions", (sessions, lock)))
        return {"stopped": 0}

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle, "stop_all_sessions", fake_stop_all_sessions)
    runtime = SimpleNamespace(
        _closed=False,
        _external_action_service=build_external_action_service_handle(
            ExternalActionServiceConfig(mode=EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN)
        ),
        _ensure_self_choice_ready=ensure_ready,
        self_choice_store=_Store(),
        tts_output=_TTS(),
        _self_choice_boot_logged=True,
        _metabolism_wakeup_event=None,
        _metabolism_task=None,
        _metabolism_runner_loop=metabolism_loop,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_maintenance_loop=lambda: None,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
        _sessions={},
        _sessions_lock=object(),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.start_background_tasks(runtime))

    assert hasattr(runtime, EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR)
    assert external_action_backend_for_runtime(runtime).mode == EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE

    runtime._metabolism_task = None
    asyncio.run(xinyu_bridge_runtime_lifecycle.shutdown(runtime))

    assert runtime._closed is True
    assert not hasattr(runtime, EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR)


def test_health_diagnostics_service_lifecycle_starts_and_stops(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Store:
        async def apply_time_decay(self) -> None:
            calls.append(("store", "decay"))

        async def shutdown(self) -> None:
            calls.append(("store", "shutdown"))

    class _HealthService:
        def start(self) -> dict[str, object]:
            calls.append(("health", "start"))
            return {"ready": True}

        def stop(self) -> dict[str, object]:
            calls.append(("health", "stop"))
            return {"ready": False}

    class _TTS:
        def close(self) -> None:
            calls.append(("tts", "close"))

    async def ensure_ready() -> None:
        calls.append(("ensure", "self_choice"))

    async def metabolism_loop() -> None:
        calls.append(("metabolism", "body"))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return _Task(done=False)

    async def fake_stop_all_sessions(sessions, lock) -> dict[str, object]:
        calls.append(("sessions", (sessions, lock)))
        return {"stopped": 0}

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle, "stop_all_sessions", fake_stop_all_sessions)
    runtime = SimpleNamespace(
        _closed=False,
        _health_diagnostics_service=_HealthService(),
        _ensure_self_choice_ready=ensure_ready,
        self_choice_store=_Store(),
        tts_output=_TTS(),
        _self_choice_boot_logged=True,
        _metabolism_wakeup_event=None,
        _metabolism_task=None,
        _metabolism_runner_loop=metabolism_loop,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_maintenance_loop=lambda: None,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
        _sessions={},
        _sessions_lock=object(),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.start_background_tasks(runtime))
    runtime._metabolism_task = None
    asyncio.run(xinyu_bridge_runtime_lifecycle.shutdown(runtime))

    assert ("health", "start") in calls
    assert ("health", "stop") in calls
    assert calls.index(("health", "start")) < calls.index(("ensure", "self_choice"))
    assert calls.index(("health", "stop")) < calls.index(("store", "shutdown"))


def test_desktop_surface_service_lifecycle_injects_and_clears_route_backend(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Store:
        async def apply_time_decay(self) -> None:
            calls.append(("store", "decay"))

        async def shutdown(self) -> None:
            calls.append(("store", "shutdown"))

    class _TTS:
        def close(self) -> None:
            calls.append(("tts", "close"))

    async def ensure_ready() -> None:
        calls.append(("ensure", "self_choice"))

    async def metabolism_loop() -> None:
        calls.append(("metabolism", "body"))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return _Task(done=False)

    async def fake_stop_all_sessions(sessions, lock) -> dict[str, object]:
        calls.append(("sessions", (sessions, lock)))
        return {"stopped": 0}

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle, "stop_all_sessions", fake_stop_all_sessions)
    runtime = SimpleNamespace(
        _closed=False,
        _desktop_surface_service=build_desktop_surface_service_handle(
            DesktopSurfaceServiceConfig(mode=DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
        ),
        desktop_event_bus=None,
        desktop_ws_server=None,
        _ensure_self_choice_ready=ensure_ready,
        self_choice_store=_Store(),
        tts_output=_TTS(),
        _self_choice_boot_logged=True,
        _metabolism_wakeup_event=None,
        _metabolism_task=None,
        _metabolism_runner_loop=metabolism_loop,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_maintenance_loop=lambda: None,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
        _sessions={},
        _sessions_lock=object(),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.start_background_tasks(runtime))

    assert hasattr(runtime, DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR)
    assert desktop_surface_route_backend_for_runtime(runtime).mode == DESKTOP_SURFACE_BACKEND_DRY_RUN_MODE

    runtime._metabolism_task = None
    asyncio.run(xinyu_bridge_runtime_lifecycle.shutdown(runtime))

    assert runtime._closed is True
    assert not hasattr(runtime, DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR)


def test_proactive_delivery_service_lifecycle_injects_and_clears_route_backend(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Store:
        async def apply_time_decay(self) -> None:
            calls.append(("store", "decay"))

        async def shutdown(self) -> None:
            calls.append(("store", "shutdown"))

    class _TTS:
        def close(self) -> None:
            calls.append(("tts", "close"))

    async def ensure_ready() -> None:
        calls.append(("ensure", "self_choice"))

    async def metabolism_loop() -> None:
        calls.append(("metabolism", "body"))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return _Task(done=False)

    async def fake_stop_all_sessions(sessions, lock) -> dict[str, object]:
        calls.append(("sessions", (sessions, lock)))
        return {"stopped": 0}

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle, "stop_all_sessions", fake_stop_all_sessions)
    runtime = SimpleNamespace(
        _closed=False,
        _proactive_delivery_service=build_proactive_delivery_service_handle(
            ProactiveDeliveryServiceConfig(mode=PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
        ),
        _ensure_self_choice_ready=ensure_ready,
        self_choice_store=_Store(),
        tts_output=_TTS(),
        _self_choice_boot_logged=True,
        _metabolism_wakeup_event=None,
        _metabolism_task=None,
        _metabolism_runner_loop=metabolism_loop,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_maintenance_loop=lambda: None,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
        _sessions={},
        _sessions_lock=object(),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.start_background_tasks(runtime))

    assert hasattr(runtime, PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR)
    assert proactive_delivery_route_backend_for_runtime(runtime).mode == PROACTIVE_DELIVERY_BACKEND_DRY_RUN_MODE

    runtime._metabolism_task = None
    asyncio.run(xinyu_bridge_runtime_lifecycle.shutdown(runtime))

    assert runtime._closed is True
    assert not hasattr(runtime, PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR)


def test_life_metabolism_service_lifecycle_injects_and_clears_route_backend(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Store:
        async def apply_time_decay(self) -> None:
            calls.append(("store", "decay"))

        async def shutdown(self) -> None:
            calls.append(("store", "shutdown"))

    class _TTS:
        def close(self) -> None:
            calls.append(("tts", "close"))

    async def ensure_ready() -> None:
        calls.append(("ensure", "self_choice"))

    async def metabolism_loop() -> None:
        calls.append(("metabolism", "body"))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return _Task(done=False)

    async def fake_stop_all_sessions(sessions, lock) -> dict[str, object]:
        calls.append(("sessions", (sessions, lock)))
        return {"stopped": 0}

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle, "stop_all_sessions", fake_stop_all_sessions)
    runtime = SimpleNamespace(
        _closed=False,
        _life_metabolism_service=build_life_metabolism_service_handle(
            LifeMetabolismServiceConfig(mode=LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
        ),
        _ensure_self_choice_ready=ensure_ready,
        self_choice_store=_Store(),
        tts_output=_TTS(),
        _self_choice_boot_logged=True,
        _metabolism_wakeup_event=None,
        _metabolism_task=None,
        _metabolism_runner_loop=metabolism_loop,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_maintenance_loop=lambda: None,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
        _sessions={},
        _sessions_lock=object(),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.start_background_tasks(runtime))

    assert hasattr(runtime, LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR)
    assert life_metabolism_route_backend_for_runtime(runtime).mode == LIFE_METABOLISM_BACKEND_DRY_RUN_MODE

    runtime._metabolism_task = None
    asyncio.run(xinyu_bridge_runtime_lifecycle.shutdown(runtime))

    assert runtime._closed is True
    assert not hasattr(runtime, LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR)


def test_learning_ingest_service_lifecycle_injects_and_clears_route_backend(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Store:
        async def apply_time_decay(self) -> None:
            calls.append(("store", "decay"))

        async def shutdown(self) -> None:
            calls.append(("store", "shutdown"))

    class _TTS:
        def close(self) -> None:
            calls.append(("tts", "close"))

    class _LearningService:
        async def ingest(self, payload):
            return payload

        async def study(self, payload):
            return payload

        async def observe(self, payload):
            return payload

    async def ensure_ready() -> None:
        calls.append(("ensure", "self_choice"))

    async def metabolism_loop() -> None:
        calls.append(("metabolism", "body"))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return _Task(done=False)

    async def fake_stop_all_sessions(sessions, lock) -> dict[str, object]:
        calls.append(("sessions", (sessions, lock)))
        return {"stopped": 0}

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle, "stop_all_sessions", fake_stop_all_sessions)
    runtime = SimpleNamespace(
        _closed=False,
        _learning_ingest_service=build_learning_ingest_service_handle(
            LearningIngestServiceConfig(mode=LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
        ),
        learning_service=_LearningService(),
        _ensure_self_choice_ready=ensure_ready,
        self_choice_store=_Store(),
        tts_output=_TTS(),
        _self_choice_boot_logged=True,
        _metabolism_wakeup_event=None,
        _metabolism_task=None,
        _metabolism_runner_loop=metabolism_loop,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_maintenance_loop=lambda: None,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
        _sessions={},
        _sessions_lock=object(),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.start_background_tasks(runtime))

    assert hasattr(runtime, LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR)
    assert learning_ingest_route_backend_for_runtime(runtime).mode == LEARNING_INGEST_BACKEND_DRY_RUN_MODE

    runtime._metabolism_task = None
    asyncio.run(xinyu_bridge_runtime_lifecycle.shutdown(runtime))

    assert runtime._closed is True
    assert not hasattr(runtime, LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR)


def test_local_report_services_lifecycle_starts_and_stops(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Store:
        async def apply_time_decay(self) -> None:
            calls.append(("store", "decay"))

        async def shutdown(self) -> None:
            calls.append(("store", "shutdown"))

    class _TTS:
        def close(self) -> None:
            calls.append(("tts", "close"))

    async def ensure_ready() -> None:
        calls.append(("ensure", "self_choice"))

    async def metabolism_loop() -> None:
        calls.append(("metabolism", "body"))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return _Task(done=False)

    async def fake_stop_all_sessions(sessions, lock) -> dict[str, object]:
        calls.append(("sessions", (sessions, lock)))
        return {"stopped": 0}

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle, "stop_all_sessions", fake_stop_all_sessions)
    runtime = SimpleNamespace(
        _closed=False,
        _diagnostic_reports_service=build_diagnostic_reports_service_handle(),
        _memory_governance_reports_service=build_memory_governance_reports_service_handle(),
        _ensure_self_choice_ready=ensure_ready,
        self_choice_store=_Store(),
        tts_output=_TTS(),
        _self_choice_boot_logged=True,
        _metabolism_wakeup_event=None,
        _metabolism_task=None,
        _metabolism_runner_loop=metabolism_loop,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_maintenance_loop=lambda: None,
        _trace_autonomous=lambda line: calls.append(("trace", line)),
        _write_autonomous_state=lambda status: calls.append(("state", status)),
        _sessions={},
        _sessions_lock=object(),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.start_background_tasks(runtime))

    assert runtime._diagnostic_reports_service.readiness().started is True
    assert runtime._memory_governance_reports_service.readiness().started is True

    runtime._metabolism_task = None
    asyncio.run(xinyu_bridge_runtime_lifecycle.shutdown(runtime))

    assert runtime._diagnostic_reports_service.readiness().started is False
    assert runtime._memory_governance_reports_service.readiness().started is False


def test_shutdown_continues_after_store_and_tts_errors(monkeypatch) -> None:
    calls: list[str] = []

    class _Store:
        async def shutdown(self) -> None:
            calls.append("store")
            raise RuntimeError("store boom")

    class _TTS:
        def close(self) -> None:
            calls.append("tts")
            raise RuntimeError("tts boom")

    async def fake_stop_all_sessions(sessions, lock) -> dict[str, object]:
        calls.append("sessions")
        return {"stopped": 0}

    monkeypatch.setattr(xinyu_bridge_runtime_lifecycle, "stop_all_sessions", fake_stop_all_sessions)
    runtime = SimpleNamespace(
        _closed=False,
        _metabolism_task=None,
        _metabolism_wakeup_event=None,
        _autonomous_task=None,
        self_choice_store=_Store(),
        tts_output=_TTS(),
        _sessions={},
        _sessions_lock=object(),
    )

    asyncio.run(xinyu_bridge_runtime_lifecycle.shutdown(runtime))

    assert runtime._closed is True
    assert calls == ["store", "tts", "sessions"]
