from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from xinyu_bridge_learning_ingest_contract import (
    learning_ingest_contract,
    learning_ingest_local_utility_route_map,
    learning_ingest_route_backend_route_map,
    learning_ingest_route_map,
)
from xinyu_bridge_learning_ingest_route_backend import (
    LEARNING_INGEST_BACKEND_DISABLED_MODE,
    LEARNING_INGEST_BACKEND_DRY_RUN_MODE,
    LEARNING_INGEST_ROUTE_BACKEND_ROLLBACK,
    LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR,
    LEARNING_INGEST_SERVICE_ID,
    DryRunLearningIngestRouteBackend,
)
from xinyu_bridge_values import as_bool, safe_str


LEARNING_INGEST_SERVICE_MODE_LOCAL = "local_only_in_process"
LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND = "local_only_dry_run_route_backend"
LEARNING_INGEST_SERVICE_CONFIG_BACKEND_ENV = "XINYU_LEARNING_INGEST_BACKEND"
LEARNING_INGEST_SERVICE_CONFIG_ROUTE_BACKEND_ENV = "XINYU_LEARNING_INGEST_ROUTE_BACKEND_ENABLED"
LEARNING_INGEST_SERVICE_METHODS = ("ingest", "study", "observe")


@dataclass(frozen=True, slots=True)
class LearningIngestServiceConfig:
    mode: str = LEARNING_INGEST_SERVICE_MODE_LOCAL


@dataclass(frozen=True, slots=True)
class LearningIngestServiceReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    local_only: bool
    process_split_candidate: bool
    process_split_ready: bool
    learning_service_available: bool
    missing_learning_service_methods: tuple[str, ...]
    api_routes: tuple[str, ...]
    runtime_facade_methods: tuple[str, ...]
    route_backend_routes: tuple[str, ...]
    local_utility_routes: tuple[str, ...]
    state_owner: str
    fallback_adapter: str
    rollback: str
    backend_config_env: str
    route_backend_config_env: str
    route_backend_enabled: bool
    route_backend_runtime_attr: str
    route_backend_mode: str
    route_backend_injected: bool
    notes: tuple[str, ...] = ()


LearningIngestRouteBackendFactory = Callable[..., DryRunLearningIngestRouteBackend]


def _normalized_mode(value: Any) -> str:
    raw = safe_str(value, LEARNING_INGEST_SERVICE_MODE_LOCAL).strip().lower()
    if raw in {"dry-run", "dry_run", "route_backend", "dry_run_route_backend", LEARNING_INGEST_BACKEND_DRY_RUN_MODE}:
        return LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    return LEARNING_INGEST_SERVICE_MODE_LOCAL


def learning_ingest_service_config_from_env(env: Mapping[str, str]) -> LearningIngestServiceConfig:
    if as_bool(env.get(LEARNING_INGEST_SERVICE_CONFIG_ROUTE_BACKEND_ENV), default=False):
        return LearningIngestServiceConfig(mode=LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    return LearningIngestServiceConfig(
        mode=_normalized_mode(env.get(LEARNING_INGEST_SERVICE_CONFIG_BACKEND_ENV))
    )


class LearningIngestServiceHandle:
    def __init__(
        self,
        config: LearningIngestServiceConfig,
        *,
        route_backend_factory: LearningIngestRouteBackendFactory = DryRunLearningIngestRouteBackend,
    ) -> None:
        self.config = config
        self._route_backend_factory = route_backend_factory
        self._started = False
        self._route_backend: DryRunLearningIngestRouteBackend | None = None
        self._injected_route_backend = False

    def start(self, runtime: Any) -> LearningIngestServiceReadiness:
        self._started = True
        self._clear_injected_backend(runtime)
        if self.config.mode == LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND:
            backend = self._route_backend_factory(enabled=True)
            self._route_backend = backend
            setattr(runtime, LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR, backend)
            self._injected_route_backend = True
        else:
            self._route_backend = None
        return self.readiness(runtime)

    def close(self, runtime: Any) -> LearningIngestServiceReadiness:
        self._clear_injected_backend(runtime)
        self._route_backend = None
        self._started = False
        return self.readiness(runtime)

    def readiness(self, runtime: Any | None = None) -> LearningIngestServiceReadiness:
        contract = learning_ingest_contract()
        missing_methods = _missing_learning_service_methods(runtime)
        route_backend_mode = (
            getattr(self._route_backend, "mode", LEARNING_INGEST_BACKEND_DISABLED_MODE)
            if self._injected_route_backend
            else LEARNING_INGEST_BACKEND_DISABLED_MODE
        )
        return LearningIngestServiceReadiness(
            service_id=LEARNING_INGEST_SERVICE_ID,
            mode=self.config.mode,
            started=self._started,
            ready=self._started and not missing_methods,
            local_only=contract.local_only,
            process_split_candidate=contract.process_split_candidate,
            process_split_ready=False,
            learning_service_available=not missing_methods,
            missing_learning_service_methods=missing_methods,
            api_routes=tuple(learning_ingest_route_map()),
            runtime_facade_methods=contract.runtime_methods,
            route_backend_routes=tuple(learning_ingest_route_backend_route_map()),
            local_utility_routes=tuple(learning_ingest_local_utility_route_map()),
            state_owner=contract.state_owner,
            fallback_adapter=contract.fallback_adapter,
            rollback=contract.rollback,
            backend_config_env=LEARNING_INGEST_SERVICE_CONFIG_BACKEND_ENV,
            route_backend_config_env=LEARNING_INGEST_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
            route_backend_enabled=self.config.mode == LEARNING_INGEST_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
            route_backend_runtime_attr=LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR,
            route_backend_mode=route_backend_mode,
            route_backend_injected=self._injected_route_backend,
            notes=(
                "local_only_runtime_service",
                "not_process_split_candidate",
                "local_utility_routes_remain_in_process",
                "route_backend_excludes_local_utility_routes",
                f"route_backend_rollback={LEARNING_INGEST_ROUTE_BACKEND_ROLLBACK}",
            ),
        )

    def _clear_injected_backend(self, runtime: Any) -> None:
        current = getattr(runtime, LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR, None)
        if self._injected_route_backend and current is self._route_backend:
            delattr(runtime, LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR)
        self._injected_route_backend = False


def _missing_learning_service_methods(runtime: Any | None) -> tuple[str, ...]:
    service = getattr(runtime, "learning_service", None)
    return tuple(
        method
        for method in LEARNING_INGEST_SERVICE_METHODS
        if not callable(getattr(service, method, None))
    )


def build_learning_ingest_service_handle(
    config: LearningIngestServiceConfig | None = None,
    *,
    route_backend_factory: LearningIngestRouteBackendFactory = DryRunLearningIngestRouteBackend,
) -> LearningIngestServiceHandle:
    return LearningIngestServiceHandle(
        LearningIngestServiceConfig() if config is None else config,
        route_backend_factory=route_backend_factory,
    )


def learning_ingest_service_readiness(runtime: Any) -> LearningIngestServiceReadiness:
    handle = getattr(runtime, "_learning_ingest_service", None)
    if handle is None:
        return build_learning_ingest_service_handle().readiness(runtime)
    return handle.readiness(runtime)
