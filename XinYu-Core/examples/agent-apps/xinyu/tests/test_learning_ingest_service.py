from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from xinyu_bridge_learning_ingest_route_backend import (
    LEARNING_INGEST_BACKEND_DISABLED_MODE,
    LEARNING_INGEST_BACKEND_DRY_RUN_MODE,
    LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR,
    learning_ingest_route_backend_for_runtime,
)
from xinyu_bridge_learning_ingest_contract import (
    learning_ingest_local_utility_route_map,
    learning_ingest_route_backend_route_map,
    learning_ingest_route_map,
)
from xinyu_bridge_learning_ingest_service import (
    LEARNING_INGEST_SERVICE_CONFIG_BACKEND_ENV,
    LEARNING_INGEST_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
    LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
    LEARNING_INGEST_SERVICE_MODE_LOCAL,
    LearningIngestServiceConfig,
    build_learning_ingest_service_handle,
    learning_ingest_service_config_from_env,
    learning_ingest_service_readiness,
)


class _LearningService:
    async def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    async def study(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload

    async def observe(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload


def test_learning_ingest_service_config_defaults_to_local() -> None:
    config = learning_ingest_service_config_from_env({})

    assert config.mode == LEARNING_INGEST_SERVICE_MODE_LOCAL


def test_learning_ingest_service_config_tracks_route_backend_env() -> None:
    assert (
        learning_ingest_service_config_from_env({"XINYU_LEARNING_INGEST_BACKEND": "dry_run"}).mode
        == LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    )
    assert (
        learning_ingest_service_config_from_env({"XINYU_LEARNING_INGEST_ROUTE_BACKEND_ENABLED": "true"}).mode
        == LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    )


def test_learning_ingest_service_default_start_keeps_routes_in_process_and_local_only() -> None:
    runtime = SimpleNamespace(learning_service=_LearningService())
    handle = build_learning_ingest_service_handle()

    readiness = handle.start(runtime)

    assert readiness.service_id == "learning_ingest"
    assert readiness.started is True
    assert readiness.ready is True
    assert readiness.local_only is True
    assert readiness.process_split_candidate is False
    assert readiness.process_split_ready is False
    assert readiness.learning_service_available is True
    assert readiness.missing_learning_service_methods == ()
    assert readiness.api_routes == tuple(learning_ingest_route_map())
    assert readiness.runtime_facade_methods == (
        "learning_ingest",
        "learning_study",
        "learning_observe",
        "sticker_import",
    )
    assert readiness.route_backend_routes == tuple(learning_ingest_route_backend_route_map())
    assert readiness.local_utility_routes == tuple(learning_ingest_local_utility_route_map())
    assert readiness.local_utility_routes == ("/sticker/import",)
    assert readiness.mode == LEARNING_INGEST_SERVICE_MODE_LOCAL
    assert readiness.backend_config_env == LEARNING_INGEST_SERVICE_CONFIG_BACKEND_ENV
    assert readiness.route_backend_config_env == LEARNING_INGEST_SERVICE_CONFIG_ROUTE_BACKEND_ENV
    assert readiness.route_backend_enabled is False
    assert readiness.route_backend_runtime_attr == LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR
    assert readiness.route_backend_mode == LEARNING_INGEST_BACKEND_DISABLED_MODE
    assert readiness.route_backend_injected is False
    assert "local_utility_routes_remain_in_process" in readiness.notes
    assert "route_backend_excludes_local_utility_routes" in readiness.notes
    assert not hasattr(runtime, LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR)
    assert learning_ingest_route_backend_for_runtime(runtime).mode == LEARNING_INGEST_BACKEND_DISABLED_MODE


def test_learning_ingest_service_reports_missing_learning_service_methods() -> None:
    runtime = SimpleNamespace(learning_service=SimpleNamespace(ingest=lambda payload: payload))
    handle = build_learning_ingest_service_handle()

    handle.start(runtime)

    readiness = learning_ingest_service_readiness(SimpleNamespace(_learning_ingest_service=handle))
    assert readiness.learning_service_available is False
    assert readiness.ready is False

    readiness = handle.readiness(runtime)
    assert readiness.learning_service_available is False
    assert readiness.missing_learning_service_methods == ("study", "observe")


def test_learning_ingest_service_dry_run_route_backend_injects_and_closes_cleanly() -> None:
    runtime = SimpleNamespace(learning_service=_LearningService())
    handle = build_learning_ingest_service_handle(
        LearningIngestServiceConfig(mode=LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    )

    readiness = handle.start(runtime)

    assert readiness.ready is True
    assert readiness.route_backend_enabled is True
    assert readiness.route_backend_runtime_attr == LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR
    assert readiness.route_backend_mode == LEARNING_INGEST_BACKEND_DRY_RUN_MODE
    assert readiness.route_backend_injected is True
    assert learning_ingest_route_backend_for_runtime(runtime).mode == LEARNING_INGEST_BACKEND_DRY_RUN_MODE

    closed = handle.close(runtime)

    assert closed.started is False
    assert closed.route_backend_injected is False
    assert not hasattr(runtime, LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR)
    assert learning_ingest_route_backend_for_runtime(runtime).mode == LEARNING_INGEST_BACKEND_DISABLED_MODE


def test_learning_ingest_service_close_preserves_foreign_route_backend() -> None:
    foreign_backend = object()
    runtime = SimpleNamespace(learning_service=_LearningService())
    handle = build_learning_ingest_service_handle(
        LearningIngestServiceConfig(mode=LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    )

    handle.start(runtime)
    setattr(runtime, LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR, foreign_backend)
    handle.close(runtime)

    assert getattr(runtime, LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR) is foreign_backend
