from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_proactive_delivery_route_backend import (
    PROACTIVE_DELIVERY_BACKEND_DISABLED_MODE,
    PROACTIVE_DELIVERY_BACKEND_DRY_RUN_MODE,
    PROACTIVE_DELIVERY_BACKEND_HTTP_MODE,
    PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR,
    HttpProactiveDeliveryRouteBackend,
    proactive_delivery_route_backend_for_runtime,
)
from xinyu_bridge_proactive_delivery_service import (
    PROACTIVE_DELIVERY_SERVICE_CONFIG_BACKEND_ENV,
    PROACTIVE_DELIVERY_SERVICE_CONFIG_ENDPOINT_ENV,
    PROACTIVE_DELIVERY_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
    PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
    PROACTIVE_DELIVERY_SERVICE_MODE_HTTP_ROUTE_BACKEND,
    PROACTIVE_DELIVERY_SERVICE_MODE_IN_PROCESS,
    ProactiveDeliveryServiceConfig,
    build_proactive_delivery_service_handle,
    proactive_delivery_service_config_from_env,
    proactive_delivery_service_readiness,
)
from xinyu_serviceization_contracts import service_contract_by_id


def test_proactive_delivery_service_config_defaults_to_in_process() -> None:
    config = proactive_delivery_service_config_from_env({})

    assert config.mode == PROACTIVE_DELIVERY_SERVICE_MODE_IN_PROCESS


def test_proactive_delivery_service_config_tracks_route_backend_env() -> None:
    assert (
        proactive_delivery_service_config_from_env({"XINYU_PROACTIVE_DELIVERY_BACKEND": "dry_run"}).mode
        == PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    )
    assert (
        proactive_delivery_service_config_from_env({"XINYU_PROACTIVE_DELIVERY_ROUTE_BACKEND_ENABLED": "true"}).mode
        == PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    )


def test_proactive_delivery_service_config_tracks_http_endpoint_env() -> None:
    config = proactive_delivery_service_config_from_env(
        {
            "XINYU_PROACTIVE_DELIVERY_BACKEND": "http",
            "XINYU_PROACTIVE_DELIVERY_ROUTE_BACKEND_ENDPOINT": "http://127.0.0.1:8787",
        }
    )

    assert config.mode == PROACTIVE_DELIVERY_SERVICE_MODE_HTTP_ROUTE_BACKEND
    assert config.endpoint == "http://127.0.0.1:8787"


def test_proactive_delivery_service_default_start_keeps_routes_in_process() -> None:
    runtime = SimpleNamespace()
    handle = build_proactive_delivery_service_handle()
    contract = service_contract_by_id("proactive_delivery")

    readiness = handle.start(runtime)

    assert readiness.service_id == "proactive_delivery"
    assert readiness.started is True
    assert readiness.ready is True
    assert readiness.mode == PROACTIVE_DELIVERY_SERVICE_MODE_IN_PROCESS
    assert readiness.api_routes == contract.api_routes
    assert readiness.runtime_facade_methods == contract.runtime_facade_methods
    assert readiness.process_split_candidate is True
    assert readiness.process_split_ready is True
    assert readiness.transport_preflight_ready is True
    assert readiness.backend_config_env == PROACTIVE_DELIVERY_SERVICE_CONFIG_BACKEND_ENV
    assert readiness.route_backend_config_env == PROACTIVE_DELIVERY_SERVICE_CONFIG_ROUTE_BACKEND_ENV
    assert readiness.endpoint_config_env == PROACTIVE_DELIVERY_SERVICE_CONFIG_ENDPOINT_ENV
    assert readiness.endpoint == ""
    assert readiness.route_backend_enabled is False
    assert readiness.route_backend_runtime_attr == PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR
    assert readiness.route_backend_mode == PROACTIVE_DELIVERY_BACKEND_DISABLED_MODE
    assert readiness.route_backend_injected is False
    assert not hasattr(runtime, PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR)
    assert proactive_delivery_route_backend_for_runtime(runtime).mode == PROACTIVE_DELIVERY_BACKEND_DISABLED_MODE


def test_proactive_delivery_service_dry_run_route_backend_injects_and_closes_cleanly() -> None:
    runtime = SimpleNamespace()
    handle = build_proactive_delivery_service_handle(
        ProactiveDeliveryServiceConfig(mode=PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    )

    readiness = handle.start(runtime)

    assert readiness.ready is True
    assert readiness.route_backend_enabled is True
    assert readiness.route_backend_runtime_attr == PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR
    assert readiness.route_backend_mode == PROACTIVE_DELIVERY_BACKEND_DRY_RUN_MODE
    assert readiness.route_backend_injected is True
    assert proactive_delivery_route_backend_for_runtime(runtime).mode == PROACTIVE_DELIVERY_BACKEND_DRY_RUN_MODE

    closed = handle.close(runtime)

    assert closed.started is False
    assert closed.route_backend_injected is False
    assert not hasattr(runtime, PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR)
    assert proactive_delivery_route_backend_for_runtime(runtime).mode == PROACTIVE_DELIVERY_BACKEND_DISABLED_MODE


def test_proactive_delivery_service_http_route_backend_injects_when_endpoint_configured() -> None:
    runtime = SimpleNamespace()
    handle = build_proactive_delivery_service_handle(
        ProactiveDeliveryServiceConfig(
            mode=PROACTIVE_DELIVERY_SERVICE_MODE_HTTP_ROUTE_BACKEND,
            endpoint="http://127.0.0.1:8787",
        )
    )

    readiness = handle.start(runtime)
    backend = proactive_delivery_route_backend_for_runtime(runtime)

    assert readiness.ready is True
    assert readiness.route_backend_enabled is True
    assert readiness.endpoint == "http://127.0.0.1:8787"
    assert readiness.route_backend_mode == PROACTIVE_DELIVERY_BACKEND_HTTP_MODE
    assert readiness.route_backend_injected is True
    assert isinstance(backend, HttpProactiveDeliveryRouteBackend)

    handle.close(runtime)


def test_proactive_delivery_service_http_route_backend_requires_endpoint() -> None:
    runtime = SimpleNamespace()
    handle = build_proactive_delivery_service_handle(
        ProactiveDeliveryServiceConfig(mode=PROACTIVE_DELIVERY_SERVICE_MODE_HTTP_ROUTE_BACKEND)
    )

    readiness = handle.start(runtime)

    assert readiness.ready is False
    assert readiness.route_backend_enabled is True
    assert readiness.endpoint == ""
    assert readiness.route_backend_mode == PROACTIVE_DELIVERY_BACKEND_DISABLED_MODE
    assert readiness.route_backend_injected is False
    assert "http_route_backend_endpoint_missing" in readiness.notes
    assert not hasattr(runtime, PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR)


def test_proactive_delivery_service_close_preserves_foreign_route_backend() -> None:
    foreign_backend = object()
    runtime = SimpleNamespace()
    handle = build_proactive_delivery_service_handle(
        ProactiveDeliveryServiceConfig(mode=PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    )

    handle.start(runtime)
    setattr(runtime, PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR, foreign_backend)
    handle.close(runtime)

    assert getattr(runtime, PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR) is foreign_backend


def test_proactive_delivery_service_readiness_uses_runtime_handle() -> None:
    runtime = SimpleNamespace()
    runtime._proactive_delivery_service = build_proactive_delivery_service_handle(
        ProactiveDeliveryServiceConfig(mode=PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    )

    runtime._proactive_delivery_service.start(runtime)
    readiness = proactive_delivery_service_readiness(runtime)

    assert readiness.started is True
    assert readiness.ready is True
    assert readiness.route_backend_mode == PROACTIVE_DELIVERY_BACKEND_DRY_RUN_MODE
