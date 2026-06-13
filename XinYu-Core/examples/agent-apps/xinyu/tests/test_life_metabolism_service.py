from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_life_metabolism_route_backend import (
    LIFE_METABOLISM_BACKEND_DISABLED_MODE,
    LIFE_METABOLISM_BACKEND_DRY_RUN_MODE,
    LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR,
    life_metabolism_route_backend_for_runtime,
)
from xinyu_bridge_life_metabolism_contract import (
    life_metabolism_route_backend_routes,
    life_metabolism_route_templates,
    life_metabolism_routes,
    life_metabolism_runtime_methods,
    life_metabolism_ticket_action_routes,
)
from xinyu_bridge_life_metabolism_service import (
    LIFE_METABOLISM_SERVICE_CONFIG_BACKEND_ENV,
    LIFE_METABOLISM_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
    LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
    LIFE_METABOLISM_SERVICE_MODE_LOCAL,
    LifeMetabolismServiceConfig,
    build_life_metabolism_service_handle,
    life_metabolism_service_config_from_env,
    life_metabolism_service_readiness,
)


class _Task:
    def __init__(self, done: bool = False) -> None:
        self._done = done

    def done(self) -> bool:
        return self._done


def test_life_metabolism_service_config_defaults_to_local() -> None:
    config = life_metabolism_service_config_from_env({})

    assert config.mode == LIFE_METABOLISM_SERVICE_MODE_LOCAL


def test_life_metabolism_service_config_tracks_route_backend_env() -> None:
    assert (
        life_metabolism_service_config_from_env({"XINYU_LIFE_METABOLISM_BACKEND": "dry_run"}).mode
        == LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    )
    assert (
        life_metabolism_service_config_from_env({"XINYU_LIFE_METABOLISM_ROUTE_BACKEND_ENABLED": "true"}).mode
        == LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    )


def test_life_metabolism_service_default_start_keeps_routes_in_process_and_local_only() -> None:
    runtime = SimpleNamespace(_metabolism_task=None)
    handle = build_life_metabolism_service_handle()

    readiness = handle.start(runtime)

    assert readiness.service_id == "life_metabolism"
    assert readiness.started is True
    assert readiness.ready is True
    assert readiness.local_only is True
    assert readiness.process_split_candidate is False
    assert readiness.process_split_ready is False
    assert readiness.api_routes == life_metabolism_routes()
    assert readiness.route_templates == life_metabolism_route_templates()
    assert readiness.runtime_facade_methods == life_metabolism_runtime_methods()
    assert readiness.route_backend_routes == life_metabolism_route_backend_routes()
    assert readiness.ticket_action_routes == life_metabolism_ticket_action_routes()
    assert readiness.dynamic_ticket_routes is True
    assert readiness.mode == LIFE_METABOLISM_SERVICE_MODE_LOCAL
    assert readiness.backend_config_env == LIFE_METABOLISM_SERVICE_CONFIG_BACKEND_ENV
    assert readiness.route_backend_config_env == LIFE_METABOLISM_SERVICE_CONFIG_ROUTE_BACKEND_ENV
    assert readiness.route_backend_enabled is False
    assert readiness.route_backend_runtime_attr == LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR
    assert readiness.route_backend_mode == LIFE_METABOLISM_BACKEND_DISABLED_MODE
    assert readiness.route_backend_injected is False
    assert readiness.runner_task_running is False
    assert "dynamic_ticket_routes_remain_in_process" in readiness.notes
    assert "route_backend_covers_ticket_templates" in readiness.notes
    assert not hasattr(runtime, LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR)
    assert life_metabolism_route_backend_for_runtime(runtime).mode == LIFE_METABOLISM_BACKEND_DISABLED_MODE


def test_life_metabolism_service_reports_runner_task_state() -> None:
    runtime = SimpleNamespace(_metabolism_task=_Task(done=False))
    handle = build_life_metabolism_service_handle()

    handle.start(runtime)

    assert life_metabolism_service_readiness(SimpleNamespace(_life_metabolism_service=handle)).runner_task_running is False
    assert handle.readiness(runtime).runner_task_running is True
    runtime._metabolism_task = _Task(done=True)
    assert handle.readiness(runtime).runner_task_running is False


def test_life_metabolism_service_dry_run_route_backend_injects_and_closes_cleanly() -> None:
    runtime = SimpleNamespace(_metabolism_task=None)
    handle = build_life_metabolism_service_handle(
        LifeMetabolismServiceConfig(mode=LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    )

    readiness = handle.start(runtime)

    assert readiness.ready is True
    assert readiness.route_backend_enabled is True
    assert readiness.route_backend_runtime_attr == LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR
    assert readiness.route_backend_mode == LIFE_METABOLISM_BACKEND_DRY_RUN_MODE
    assert readiness.route_backend_injected is True
    assert life_metabolism_route_backend_for_runtime(runtime).mode == LIFE_METABOLISM_BACKEND_DRY_RUN_MODE

    closed = handle.close(runtime)

    assert closed.started is False
    assert closed.route_backend_injected is False
    assert not hasattr(runtime, LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR)
    assert life_metabolism_route_backend_for_runtime(runtime).mode == LIFE_METABOLISM_BACKEND_DISABLED_MODE


def test_life_metabolism_service_close_preserves_foreign_route_backend() -> None:
    foreign_backend = object()
    runtime = SimpleNamespace(_metabolism_task=None)
    handle = build_life_metabolism_service_handle(
        LifeMetabolismServiceConfig(mode=LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    )

    handle.start(runtime)
    setattr(runtime, LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR, foreign_backend)
    handle.close(runtime)

    assert getattr(runtime, LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR) is foreign_backend
