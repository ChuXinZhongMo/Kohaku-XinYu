from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from xinyu_bridge_life_metabolism_contract import (
    LIFE_METABOLISM_FALLBACK_ADAPTER,
    LIFE_METABOLISM_ROLLBACK,
    LIFE_METABOLISM_STATE_OWNER,
    life_metabolism_route_backend_routes,
    life_metabolism_route_templates,
    life_metabolism_routes,
    life_metabolism_runtime_methods,
    life_metabolism_ticket_action_routes,
)
from xinyu_bridge_life_metabolism_route_backend import (
    LIFE_METABOLISM_BACKEND_DISABLED_MODE,
    LIFE_METABOLISM_BACKEND_DRY_RUN_MODE,
    LIFE_METABOLISM_ROUTE_BACKEND_ROLLBACK,
    LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR,
    DryRunLifeMetabolismRouteBackend,
)
from xinyu_bridge_values import as_bool, safe_str


LIFE_METABOLISM_SERVICE_ID = "life_metabolism"
LIFE_METABOLISM_SERVICE_MODE_LOCAL = "local_only_in_process"
LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND = "local_only_dry_run_route_backend"
LIFE_METABOLISM_SERVICE_CONFIG_BACKEND_ENV = "XINYU_LIFE_METABOLISM_BACKEND"
LIFE_METABOLISM_SERVICE_CONFIG_ROUTE_BACKEND_ENV = "XINYU_LIFE_METABOLISM_ROUTE_BACKEND_ENABLED"


@dataclass(frozen=True, slots=True)
class LifeMetabolismServiceConfig:
    mode: str = LIFE_METABOLISM_SERVICE_MODE_LOCAL


@dataclass(frozen=True, slots=True)
class LifeMetabolismServiceReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    local_only: bool
    process_split_candidate: bool
    process_split_ready: bool
    api_routes: tuple[str, ...]
    route_templates: tuple[str, ...]
    runtime_facade_methods: tuple[str, ...]
    route_backend_routes: tuple[str, ...]
    ticket_action_routes: tuple[str, ...]
    dynamic_ticket_routes: bool
    state_owner: str
    fallback_adapter: str
    rollback: str
    backend_config_env: str
    route_backend_config_env: str
    route_backend_enabled: bool
    route_backend_runtime_attr: str
    route_backend_mode: str
    route_backend_injected: bool
    runner_task_running: bool
    notes: tuple[str, ...] = ()


LifeMetabolismRouteBackendFactory = Callable[..., DryRunLifeMetabolismRouteBackend]


def _normalized_mode(value: Any) -> str:
    raw = safe_str(value, LIFE_METABOLISM_SERVICE_MODE_LOCAL).strip().lower()
    if raw in {"dry-run", "dry_run", "route_backend", "dry_run_route_backend", LIFE_METABOLISM_BACKEND_DRY_RUN_MODE}:
        return LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    return LIFE_METABOLISM_SERVICE_MODE_LOCAL


def life_metabolism_service_config_from_env(env: Mapping[str, str]) -> LifeMetabolismServiceConfig:
    if as_bool(env.get(LIFE_METABOLISM_SERVICE_CONFIG_ROUTE_BACKEND_ENV), default=False):
        return LifeMetabolismServiceConfig(mode=LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    return LifeMetabolismServiceConfig(
        mode=_normalized_mode(env.get(LIFE_METABOLISM_SERVICE_CONFIG_BACKEND_ENV))
    )


class LifeMetabolismServiceHandle:
    def __init__(
        self,
        config: LifeMetabolismServiceConfig,
        *,
        route_backend_factory: LifeMetabolismRouteBackendFactory = DryRunLifeMetabolismRouteBackend,
    ) -> None:
        self.config = config
        self._route_backend_factory = route_backend_factory
        self._started = False
        self._route_backend: DryRunLifeMetabolismRouteBackend | None = None
        self._injected_route_backend = False

    def start(self, runtime: Any) -> LifeMetabolismServiceReadiness:
        self._started = True
        self._clear_injected_backend(runtime)
        if self.config.mode == LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND:
            backend = self._route_backend_factory(enabled=True)
            self._route_backend = backend
            setattr(runtime, LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR, backend)
            self._injected_route_backend = True
        else:
            self._route_backend = None
        return self.readiness(runtime)

    def close(self, runtime: Any) -> LifeMetabolismServiceReadiness:
        self._clear_injected_backend(runtime)
        self._route_backend = None
        self._started = False
        return self.readiness(runtime)

    def readiness(self, runtime: Any | None = None) -> LifeMetabolismServiceReadiness:
        task = getattr(runtime, "_metabolism_task", None)
        route_backend_mode = (
            getattr(self._route_backend, "mode", LIFE_METABOLISM_BACKEND_DISABLED_MODE)
            if self._injected_route_backend
            else LIFE_METABOLISM_BACKEND_DISABLED_MODE
        )
        return LifeMetabolismServiceReadiness(
            service_id=LIFE_METABOLISM_SERVICE_ID,
            mode=self.config.mode,
            started=self._started,
            ready=self._started,
            local_only=True,
            process_split_candidate=False,
            process_split_ready=False,
            api_routes=life_metabolism_routes(),
            route_templates=life_metabolism_route_templates(),
            runtime_facade_methods=life_metabolism_runtime_methods(),
            route_backend_routes=life_metabolism_route_backend_routes(),
            ticket_action_routes=life_metabolism_ticket_action_routes(),
            dynamic_ticket_routes=True,
            state_owner=LIFE_METABOLISM_STATE_OWNER,
            fallback_adapter=LIFE_METABOLISM_FALLBACK_ADAPTER,
            rollback=LIFE_METABOLISM_ROLLBACK,
            backend_config_env=LIFE_METABOLISM_SERVICE_CONFIG_BACKEND_ENV,
            route_backend_config_env=LIFE_METABOLISM_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
            route_backend_enabled=self.config.mode == LIFE_METABOLISM_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
            route_backend_runtime_attr=LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR,
            route_backend_mode=route_backend_mode,
            route_backend_injected=self._injected_route_backend,
            runner_task_running=bool(task is not None and not task.done()),
            notes=(
                "local_only_runtime_service",
                "not_process_split_candidate",
                "dynamic_ticket_routes_remain_in_process",
                "route_backend_covers_ticket_templates",
                f"route_backend_rollback={LIFE_METABOLISM_ROUTE_BACKEND_ROLLBACK}",
            ),
        )

    def _clear_injected_backend(self, runtime: Any) -> None:
        current = getattr(runtime, LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR, None)
        if self._injected_route_backend and current is self._route_backend:
            delattr(runtime, LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR)
        self._injected_route_backend = False


def build_life_metabolism_service_handle(
    config: LifeMetabolismServiceConfig | None = None,
    *,
    route_backend_factory: LifeMetabolismRouteBackendFactory = DryRunLifeMetabolismRouteBackend,
) -> LifeMetabolismServiceHandle:
    return LifeMetabolismServiceHandle(
        LifeMetabolismServiceConfig() if config is None else config,
        route_backend_factory=route_backend_factory,
    )


def life_metabolism_service_readiness(runtime: Any) -> LifeMetabolismServiceReadiness:
    handle = getattr(runtime, "_life_metabolism_service", None)
    if handle is None:
        return build_life_metabolism_service_handle().readiness(runtime)
    return handle.readiness(runtime)
