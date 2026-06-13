from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_codex_execution_backend import (
    CODEX_EXECUTION_BACKEND_RUNTIME_ATTR,
    CODEX_EXECUTION_IN_PROCESS_BACKEND,
    codex_execution_backend_for_runtime,
)
from xinyu_bridge_codex_execution_contract import (
    CODEX_EXECUTION_FALLBACK_ADAPTER,
    CODEX_EXECUTION_ROLLBACK,
    CODEX_EXECUTION_STATE_OWNER,
)
from xinyu_bridge_codex_execution_service import (
    CODEX_EXECUTION_SERVICE_MODE_IN_PROCESS,
    CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT,
    CodexExecutionServiceConfig,
    build_codex_execution_service_handle,
    codex_execution_service_config_from_env,
    codex_execution_service_readiness,
)
from xinyu_bridge_codex_execution_worker_client import (
    CODEX_EXECUTION_HTTP_WORKER_CLIENT_MODE,
    CODEX_EXECUTION_WORKER_CLIENT_MODE,
    DryRunCodexExecutionWorkerClient,
    HttpCodexExecutionWorkerClient,
)
from xinyu_serviceization_contracts import service_contract_by_id


def test_codex_execution_service_config_defaults_to_in_process() -> None:
    config = codex_execution_service_config_from_env({})

    assert config.mode == CODEX_EXECUTION_SERVICE_MODE_IN_PROCESS
    assert config.endpoint == ""
    assert config.worker_enabled is False
    assert config.worker_healthy is True
    assert config.fallback_on_unhealthy is True
    assert config.health_timeout_seconds == 5
    assert config.submit_timeout_seconds == 30
    assert config.cancel_timeout_seconds == 10


def test_codex_execution_service_config_tracks_worker_client_env() -> None:
    config = codex_execution_service_config_from_env(
        {
            "XINYU_CODEX_EXECUTION_BACKEND": "worker_client",
            "XINYU_CODEX_EXECUTION_WORKER_ENDPOINT": "http://127.0.0.1:8787",
            "XINYU_CODEX_EXECUTION_WORKER_ENABLED": "true",
            "XINYU_CODEX_EXECUTION_WORKER_HEALTHY": "false",
            "XINYU_CODEX_EXECUTION_FALLBACK_ON_UNHEALTHY": "false",
            "XINYU_CODEX_EXECUTION_HEALTH_TIMEOUT_SECONDS": "0",
            "XINYU_CODEX_EXECUTION_SUBMIT_TIMEOUT_SECONDS": "42",
            "XINYU_CODEX_EXECUTION_CANCEL_TIMEOUT_SECONDS": "bad",
        }
    )

    assert config.mode == CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT
    assert config.endpoint == "http://127.0.0.1:8787"
    assert config.worker_enabled is True
    assert config.worker_healthy is False
    assert config.fallback_on_unhealthy is False
    assert config.health_timeout_seconds == 1
    assert config.submit_timeout_seconds == 42
    assert config.cancel_timeout_seconds == 10


def test_codex_execution_service_default_start_keeps_runtime_in_process() -> None:
    runtime = SimpleNamespace()
    handle = build_codex_execution_service_handle()

    readiness = handle.start(runtime)

    assert readiness.service_id == "codex_execution"
    assert readiness.started is True
    assert readiness.ready is True
    assert readiness.backend_mode == CODEX_EXECUTION_IN_PROCESS_BACKEND
    assert readiness.injected_runtime_backend is False
    assert readiness.worker_enabled is False
    assert readiness.worker_healthy is True
    assert readiness.fallback_on_unhealthy is True
    assert readiness.health_timeout_seconds == 5
    assert readiness.submit_timeout_seconds == 30
    assert readiness.cancel_timeout_seconds == 10
    assert "no_external_worker_started" in readiness.notes
    assert not hasattr(runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR)
    assert codex_execution_backend_for_runtime(runtime).mode == CODEX_EXECUTION_IN_PROCESS_BACKEND


def test_codex_execution_service_readiness_exposes_service_contract_metadata() -> None:
    contract = service_contract_by_id("codex_execution")
    handle = build_codex_execution_service_handle()

    initial = handle.readiness()
    started = handle.start(SimpleNamespace())

    for readiness in (initial, started):
        assert readiness.service_id == contract.service_id
        assert readiness.api_routes == contract.api_routes
        assert readiness.runtime_facade_methods == contract.runtime_facade_methods
        assert readiness.process_split_candidate is contract.process_split_candidate
        assert readiness.process_split_ready is contract.process_split_ready
        assert readiness.process_split_gate == contract.process_split_gate
        assert readiness.state_owner == CODEX_EXECUTION_STATE_OWNER
        assert readiness.fallback_adapter == CODEX_EXECUTION_FALLBACK_ADAPTER
        assert readiness.rollback == CODEX_EXECUTION_ROLLBACK


def test_codex_execution_service_readiness_exposes_worker_config() -> None:
    config = CodexExecutionServiceConfig(
        mode=CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT,
        endpoint="http://127.0.0.1:8787",
        worker_enabled=True,
        worker_healthy=False,
        fallback_on_unhealthy=False,
        health_timeout_seconds=2,
        submit_timeout_seconds=3,
        cancel_timeout_seconds=4,
    )
    handle = build_codex_execution_service_handle(config)

    readiness = handle.start(SimpleNamespace())

    assert readiness.endpoint == "http://127.0.0.1:8787"
    assert readiness.worker_enabled is True
    assert readiness.worker_healthy is False
    assert readiness.fallback_on_unhealthy is False
    assert readiness.health_timeout_seconds == 2
    assert readiness.submit_timeout_seconds == 3
    assert readiness.cancel_timeout_seconds == 4
    assert readiness.ready is False
    assert readiness.backend_mode == CODEX_EXECUTION_HTTP_WORKER_CLIENT_MODE


def test_codex_execution_service_worker_client_injects_backend_when_ready() -> None:
    runtime = SimpleNamespace()
    handle = build_codex_execution_service_handle(
        CodexExecutionServiceConfig(
            mode=CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT,
            worker_enabled=True,
            worker_healthy=True,
        )
    )

    readiness = handle.start(runtime)
    backend = codex_execution_backend_for_runtime(runtime)

    assert readiness.ready is True
    assert readiness.backend_mode == CODEX_EXECUTION_WORKER_CLIENT_MODE
    assert readiness.injected_runtime_backend is True
    assert isinstance(backend, DryRunCodexExecutionWorkerClient)
    assert backend.readiness().ready is True

    closed = handle.close(runtime)
    assert closed.started is False
    assert closed.injected_runtime_backend is False
    assert not hasattr(runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR)
    assert codex_execution_backend_for_runtime(runtime).mode == CODEX_EXECUTION_IN_PROCESS_BACKEND


def test_codex_execution_service_endpoint_selects_http_worker_client_when_ready() -> None:
    runtime = SimpleNamespace()
    handle = build_codex_execution_service_handle(
        CodexExecutionServiceConfig(
            mode=CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT,
            endpoint="http://127.0.0.1:8787",
            worker_enabled=True,
            worker_healthy=True,
        )
    )

    readiness = handle.start(runtime)
    backend = codex_execution_backend_for_runtime(runtime)

    assert readiness.ready is True
    assert readiness.backend_mode == CODEX_EXECUTION_HTTP_WORKER_CLIENT_MODE
    assert readiness.injected_runtime_backend is True
    assert isinstance(backend, HttpCodexExecutionWorkerClient)

    handle.close(runtime)


def test_codex_execution_service_unhealthy_worker_falls_back_without_injection() -> None:
    runtime = SimpleNamespace()
    handle = build_codex_execution_service_handle(
        CodexExecutionServiceConfig(
            mode=CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT,
            worker_enabled=True,
            worker_healthy=False,
            fallback_on_unhealthy=True,
        )
    )

    readiness = handle.start(runtime)

    assert readiness.started is True
    assert readiness.ready is True
    assert readiness.backend_mode == CODEX_EXECUTION_IN_PROCESS_BACKEND
    assert readiness.injected_runtime_backend is False
    assert "worker_client_not_ready" in readiness.notes
    assert "fallback_to_in_process_backend" in readiness.notes
    assert not hasattr(runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR)
    assert codex_execution_backend_for_runtime(runtime).mode == CODEX_EXECUTION_IN_PROCESS_BACKEND


def test_codex_execution_service_readiness_uses_runtime_handle() -> None:
    runtime = SimpleNamespace(_codex_execution_service=build_codex_execution_service_handle())

    runtime._codex_execution_service.start(runtime)
    readiness = codex_execution_service_readiness(runtime)

    assert readiness.started is True
    assert readiness.backend_mode == CODEX_EXECUTION_IN_PROCESS_BACKEND
