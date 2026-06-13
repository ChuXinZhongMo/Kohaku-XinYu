from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_external_action_backend import (
    EXTERNAL_ACTION_BACKEND_DISABLED_MODE,
    EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE,
    EXTERNAL_ACTION_BACKEND_HTTP_MODE,
    EXTERNAL_ACTION_BACKEND_ROLLBACK,
    EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR,
    HttpExternalActionExecutionBackend,
    external_action_backend_for_runtime,
)
from xinyu_bridge_external_action_contract import EXTERNAL_ACTION_ROLLBACK, EXTERNAL_ACTION_STATE_OWNER
from xinyu_bridge_external_action_service import (
    EXTERNAL_ACTION_SERVICE_CONFIG_BACKEND_ENV,
    EXTERNAL_ACTION_SERVICE_CONFIG_DRY_RUN_ENV,
    EXTERNAL_ACTION_SERVICE_CONFIG_ENDPOINT_ENV,
    EXTERNAL_ACTION_SERVICE_MODE_DISABLED,
    EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN,
    EXTERNAL_ACTION_SERVICE_MODE_HTTP,
    ExternalActionServiceConfig,
    build_external_action_service_handle,
    external_action_service_config_from_env,
    external_action_service_readiness,
)
from xinyu_serviceization_contracts import service_contract_by_id


def test_external_action_service_config_defaults_to_disabled() -> None:
    config = external_action_service_config_from_env({})

    assert config.mode == EXTERNAL_ACTION_SERVICE_MODE_DISABLED


def test_external_action_service_config_tracks_dry_run_env() -> None:
    assert (
        external_action_service_config_from_env(
            {"XINYU_EXTERNAL_ACTION_BACKEND": "dry_run"}
        ).mode
        == EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN
    )
    assert (
        external_action_service_config_from_env(
            {"XINYU_EXTERNAL_ACTION_DRY_RUN_ENABLED": "true"}
        ).mode
        == EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN
    )


def test_external_action_service_config_tracks_http_endpoint_env() -> None:
    config = external_action_service_config_from_env(
        {
            "XINYU_EXTERNAL_ACTION_BACKEND": "http",
            "XINYU_EXTERNAL_ACTION_BACKEND_ENDPOINT": "http://127.0.0.1:8787",
        }
    )

    assert config.mode == EXTERNAL_ACTION_SERVICE_MODE_HTTP
    assert config.endpoint == "http://127.0.0.1:8787"


def test_external_action_service_default_start_keeps_runtime_routes_in_process() -> None:
    runtime = SimpleNamespace()
    handle = build_external_action_service_handle()

    readiness = handle.start(runtime)

    assert readiness.service_id == "external_action"
    assert readiness.started is True
    assert readiness.ready is False
    assert readiness.backend_config_env == EXTERNAL_ACTION_SERVICE_CONFIG_BACKEND_ENV
    assert readiness.dry_run_config_env == EXTERNAL_ACTION_SERVICE_CONFIG_DRY_RUN_ENV
    assert readiness.endpoint_config_env == EXTERNAL_ACTION_SERVICE_CONFIG_ENDPOINT_ENV
    assert readiness.endpoint == ""
    assert readiness.backend_enabled is False
    assert readiness.backend_runtime_attr == EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR
    assert readiness.backend_mode == EXTERNAL_ACTION_BACKEND_DISABLED_MODE
    assert readiness.injected_runtime_backend is False
    assert "current_routes_use_in_process_facades" in readiness.notes
    assert not hasattr(runtime, EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR)
    assert external_action_backend_for_runtime(runtime).mode == EXTERNAL_ACTION_BACKEND_DISABLED_MODE


def test_external_action_service_readiness_matches_serviceization_contract_metadata() -> None:
    contract = service_contract_by_id("external_action")
    runtime = SimpleNamespace()
    handle = build_external_action_service_handle(
        ExternalActionServiceConfig(mode=EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN)
    )

    for readiness in (
        handle.readiness(),
        handle.start(runtime),
        external_action_service_readiness(SimpleNamespace(_external_action_service=handle)),
    ):
        assert readiness.service_id == contract.service_id
        assert readiness.api_routes == contract.api_routes
        assert readiness.runtime_facade_methods == contract.runtime_facade_methods
        assert readiness.process_split_candidate is contract.process_split_candidate
        assert readiness.process_split_ready is contract.process_split_ready
        assert readiness.state_owner == EXTERNAL_ACTION_STATE_OWNER
        assert readiness.fallback_adapter == "in_process_runtime_route_methods"
        assert readiness.rollback == EXTERNAL_ACTION_ROLLBACK
        assert readiness.backend_config_env == EXTERNAL_ACTION_SERVICE_CONFIG_BACKEND_ENV
        assert readiness.dry_run_config_env == EXTERNAL_ACTION_SERVICE_CONFIG_DRY_RUN_ENV
        assert readiness.endpoint_config_env == EXTERNAL_ACTION_SERVICE_CONFIG_ENDPOINT_ENV
        assert readiness.backend_runtime_attr == EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR
        assert readiness.backend_rollback == EXTERNAL_ACTION_BACKEND_ROLLBACK
        assert readiness.backend_mode in {
            EXTERNAL_ACTION_BACKEND_DISABLED_MODE,
            EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE,
        }


def test_external_action_service_dry_run_injects_backend_and_closes_cleanly() -> None:
    runtime = SimpleNamespace()
    handle = build_external_action_service_handle(
        ExternalActionServiceConfig(mode=EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN)
    )

    readiness = handle.start(runtime)

    assert readiness.ready is True
    assert readiness.backend_enabled is True
    assert readiness.backend_runtime_attr == EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR
    assert readiness.backend_mode == EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE
    assert readiness.injected_runtime_backend is True
    assert external_action_backend_for_runtime(runtime).mode == EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE

    closed = handle.close(runtime)

    assert closed.started is False
    assert closed.injected_runtime_backend is False
    assert not hasattr(runtime, EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR)
    assert external_action_backend_for_runtime(runtime).mode == EXTERNAL_ACTION_BACKEND_DISABLED_MODE


def test_external_action_service_http_backend_injects_when_endpoint_configured() -> None:
    runtime = SimpleNamespace()
    handle = build_external_action_service_handle(
        ExternalActionServiceConfig(
            mode=EXTERNAL_ACTION_SERVICE_MODE_HTTP,
            endpoint="http://127.0.0.1:8787",
        )
    )

    readiness = handle.start(runtime)
    backend = external_action_backend_for_runtime(runtime)

    assert readiness.ready is True
    assert readiness.backend_enabled is True
    assert readiness.endpoint == "http://127.0.0.1:8787"
    assert readiness.backend_mode == EXTERNAL_ACTION_BACKEND_HTTP_MODE
    assert readiness.injected_runtime_backend is True
    assert isinstance(backend, HttpExternalActionExecutionBackend)

    handle.close(runtime)


def test_external_action_service_http_backend_requires_endpoint() -> None:
    runtime = SimpleNamespace()
    handle = build_external_action_service_handle(
        ExternalActionServiceConfig(mode=EXTERNAL_ACTION_SERVICE_MODE_HTTP)
    )

    readiness = handle.start(runtime)

    assert readiness.ready is False
    assert readiness.backend_enabled is True
    assert readiness.endpoint == ""
    assert readiness.backend_mode == EXTERNAL_ACTION_BACKEND_DISABLED_MODE
    assert readiness.injected_runtime_backend is False
    assert "configured_http_backend_missing_endpoint" in readiness.notes
    assert not hasattr(runtime, EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR)


def test_external_action_service_close_preserves_foreign_runtime_backend() -> None:
    foreign_backend = object()
    runtime = SimpleNamespace(**{EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR: foreign_backend})
    handle = build_external_action_service_handle(
        ExternalActionServiceConfig(mode=EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN)
    )

    handle.start(runtime)
    setattr(runtime, EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR, foreign_backend)
    handle.close(runtime)

    assert getattr(runtime, EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR) is foreign_backend


def test_external_action_service_readiness_uses_runtime_handle() -> None:
    runtime = SimpleNamespace(
        _external_action_service=build_external_action_service_handle(
            ExternalActionServiceConfig(mode=EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN)
        )
    )

    runtime._external_action_service.start(runtime)
    readiness = external_action_service_readiness(runtime)

    assert readiness.started is True
    assert readiness.ready is True
    assert readiness.backend_mode == EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE
