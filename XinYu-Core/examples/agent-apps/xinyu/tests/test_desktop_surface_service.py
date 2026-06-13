from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_desktop_surface_route_backend import (
    DESKTOP_SURFACE_BACKEND_DISABLED_MODE,
    DESKTOP_SURFACE_BACKEND_DRY_RUN_MODE,
    DESKTOP_SURFACE_BACKEND_HTTP_MODE,
    DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR,
    HttpDesktopSurfaceRouteBackend,
    desktop_surface_route_backend_for_runtime,
)
from xinyu_bridge_desktop_surface_service import (
    DESKTOP_SURFACE_SERVICE_CONFIG_BACKEND_ENV,
    DESKTOP_SURFACE_SERVICE_CONFIG_ENDPOINT_ENV,
    DESKTOP_SURFACE_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
    DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
    DESKTOP_SURFACE_SERVICE_MODE_HTTP_ROUTE_BACKEND,
    DESKTOP_SURFACE_SERVICE_MODE_IN_PROCESS,
    DesktopSurfaceServiceConfig,
    build_desktop_surface_service_handle,
    desktop_surface_service_config_from_env,
    desktop_surface_service_readiness,
)
from xinyu_serviceization_contracts import service_contract_by_id


def test_desktop_surface_service_config_defaults_to_in_process() -> None:
    config = desktop_surface_service_config_from_env({})

    assert config.mode == DESKTOP_SURFACE_SERVICE_MODE_IN_PROCESS


def test_desktop_surface_service_config_tracks_route_backend_env() -> None:
    assert (
        desktop_surface_service_config_from_env({"XINYU_DESKTOP_SURFACE_BACKEND": "dry_run"}).mode
        == DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    )
    assert (
        desktop_surface_service_config_from_env({"XINYU_DESKTOP_SURFACE_ROUTE_BACKEND_ENABLED": "true"}).mode
        == DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    )


def test_desktop_surface_service_config_tracks_http_endpoint_env() -> None:
    config = desktop_surface_service_config_from_env(
        {
            "XINYU_DESKTOP_SURFACE_BACKEND": "http",
            "XINYU_DESKTOP_SURFACE_ROUTE_BACKEND_ENDPOINT": "http://127.0.0.1:8787",
        }
    )

    assert config.mode == DESKTOP_SURFACE_SERVICE_MODE_HTTP_ROUTE_BACKEND
    assert config.endpoint == "http://127.0.0.1:8787"


def test_desktop_surface_service_default_start_keeps_routes_in_process() -> None:
    contract = service_contract_by_id("desktop_surface")
    runtime = SimpleNamespace(desktop_event_bus=None, desktop_ws_server=None)
    handle = build_desktop_surface_service_handle()

    readiness = handle.start(runtime)

    assert readiness.service_id == "desktop_surface"
    assert readiness.started is True
    assert readiness.ready is True
    assert readiness.mode == DESKTOP_SURFACE_SERVICE_MODE_IN_PROCESS
    assert readiness.api_routes == contract.api_routes
    assert readiness.runtime_facade_methods == contract.runtime_facade_methods
    assert readiness.process_split_candidate is contract.process_split_candidate
    assert readiness.process_split_ready is contract.process_split_ready
    assert readiness.event_stream.status == "disabled"
    assert readiness.backend == DESKTOP_SURFACE_BACKEND_DISABLED_MODE
    assert readiness.backend_config_env == DESKTOP_SURFACE_SERVICE_CONFIG_BACKEND_ENV
    assert readiness.route_backend_config_env == DESKTOP_SURFACE_SERVICE_CONFIG_ROUTE_BACKEND_ENV
    assert readiness.endpoint_config_env == DESKTOP_SURFACE_SERVICE_CONFIG_ENDPOINT_ENV
    assert readiness.endpoint == ""
    assert readiness.route_backend_enabled is False
    assert readiness.route_backend_runtime_attr == DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR
    assert readiness.route_backend_mode == DESKTOP_SURFACE_BACKEND_DISABLED_MODE
    assert readiness.route_backend_injected is False
    assert not hasattr(runtime, DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR)
    assert desktop_surface_route_backend_for_runtime(runtime).mode == DESKTOP_SURFACE_BACKEND_DISABLED_MODE


def test_desktop_surface_service_readiness_metadata_matches_contract() -> None:
    contract = service_contract_by_id("desktop_surface")
    readiness = build_desktop_surface_service_handle().readiness(
        SimpleNamespace(desktop_event_bus=None, desktop_ws_server=None)
    )

    assert readiness.api_routes == contract.api_routes
    assert readiness.runtime_facade_methods == contract.runtime_facade_methods
    assert readiness.process_split_candidate is True
    assert readiness.process_split_ready is True
    assert readiness.process_split_candidate is contract.process_split_candidate
    assert readiness.process_split_ready is contract.process_split_ready


def test_desktop_surface_service_dry_run_route_backend_injects_and_closes_cleanly() -> None:
    runtime = SimpleNamespace(desktop_event_bus=None, desktop_ws_server=None)
    handle = build_desktop_surface_service_handle(
        DesktopSurfaceServiceConfig(mode=DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    )

    readiness = handle.start(runtime)

    assert readiness.ready is True
    assert readiness.route_backend_enabled is True
    assert readiness.route_backend_runtime_attr == DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR
    assert readiness.route_backend_mode == DESKTOP_SURFACE_BACKEND_DRY_RUN_MODE
    assert readiness.route_backend_injected is True
    assert desktop_surface_route_backend_for_runtime(runtime).mode == DESKTOP_SURFACE_BACKEND_DRY_RUN_MODE

    closed = handle.close(runtime)

    assert closed.started is False
    assert closed.route_backend_injected is False
    assert not hasattr(runtime, DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR)
    assert desktop_surface_route_backend_for_runtime(runtime).mode == DESKTOP_SURFACE_BACKEND_DISABLED_MODE


def test_desktop_surface_service_http_route_backend_injects_when_endpoint_configured() -> None:
    runtime = SimpleNamespace(desktop_event_bus=None, desktop_ws_server=None)
    handle = build_desktop_surface_service_handle(
        DesktopSurfaceServiceConfig(
            mode=DESKTOP_SURFACE_SERVICE_MODE_HTTP_ROUTE_BACKEND,
            endpoint="http://127.0.0.1:8787",
        )
    )

    readiness = handle.start(runtime)
    backend = desktop_surface_route_backend_for_runtime(runtime)

    assert readiness.ready is True
    assert readiness.route_backend_enabled is True
    assert readiness.endpoint == "http://127.0.0.1:8787"
    assert readiness.route_backend_mode == DESKTOP_SURFACE_BACKEND_HTTP_MODE
    assert readiness.route_backend_injected is True
    assert isinstance(backend, HttpDesktopSurfaceRouteBackend)

    handle.close(runtime)


def test_desktop_surface_service_http_route_backend_requires_endpoint() -> None:
    runtime = SimpleNamespace(desktop_event_bus=None, desktop_ws_server=None)
    handle = build_desktop_surface_service_handle(
        DesktopSurfaceServiceConfig(mode=DESKTOP_SURFACE_SERVICE_MODE_HTTP_ROUTE_BACKEND)
    )

    readiness = handle.start(runtime)

    assert readiness.ready is False
    assert readiness.route_backend_enabled is True
    assert readiness.endpoint == ""
    assert readiness.route_backend_mode == DESKTOP_SURFACE_BACKEND_DISABLED_MODE
    assert readiness.route_backend_injected is False
    assert "http_route_backend_endpoint_missing" in readiness.notes
    assert not hasattr(runtime, DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR)


def test_desktop_surface_service_close_preserves_foreign_route_backend() -> None:
    foreign_backend = object()
    runtime = SimpleNamespace(desktop_event_bus=None, desktop_ws_server=None)
    handle = build_desktop_surface_service_handle(
        DesktopSurfaceServiceConfig(mode=DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    )

    handle.start(runtime)
    setattr(runtime, DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR, foreign_backend)
    handle.close(runtime)

    assert getattr(runtime, DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR) is foreign_backend


def test_desktop_surface_service_readiness_uses_runtime_handle() -> None:
    runtime = SimpleNamespace(desktop_event_bus=None, desktop_ws_server=None)
    runtime._desktop_surface_service = build_desktop_surface_service_handle(
        DesktopSurfaceServiceConfig(mode=DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    )

    runtime._desktop_surface_service.start(runtime)
    readiness = desktop_surface_service_readiness(runtime)

    assert readiness.started is True
    assert readiness.ready is True
    assert readiness.route_backend_mode == DESKTOP_SURFACE_BACKEND_DRY_RUN_MODE
