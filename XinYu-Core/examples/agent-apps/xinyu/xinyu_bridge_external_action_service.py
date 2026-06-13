from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from xinyu_bridge_external_action_backend import (
    EXTERNAL_ACTION_BACKEND_DISABLED_MODE,
    EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE,
    EXTERNAL_ACTION_BACKEND_HTTP_MODE,
    EXTERNAL_ACTION_BACKEND_ROLLBACK,
    EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR,
    EXTERNAL_ACTION_SERVICE_ID,
    DryRunExternalActionExecutionBackend,
    HttpExternalActionExecutionBackend,
    build_external_action_execution_backend,
)
from xinyu_bridge_external_action_contract import (
    EXTERNAL_ACTION_FALLBACK_ADAPTER,
    EXTERNAL_ACTION_ROLLBACK,
    EXTERNAL_ACTION_STATE_OWNER,
)
from xinyu_bridge_values import as_bool, safe_str
from xinyu_serviceization_contracts import service_contract_by_id


EXTERNAL_ACTION_SERVICE_MODE_DISABLED = "disabled"
EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN = "dry_run"
EXTERNAL_ACTION_SERVICE_MODE_HTTP = "http"
EXTERNAL_ACTION_SERVICE_CONFIG_BACKEND_ENV = "XINYU_EXTERNAL_ACTION_BACKEND"
EXTERNAL_ACTION_SERVICE_CONFIG_DRY_RUN_ENV = "XINYU_EXTERNAL_ACTION_DRY_RUN_ENABLED"
EXTERNAL_ACTION_SERVICE_CONFIG_ENDPOINT_ENV = "XINYU_EXTERNAL_ACTION_BACKEND_ENDPOINT"
EXTERNAL_ACTION_SERVICE_CONTRACT = service_contract_by_id(EXTERNAL_ACTION_SERVICE_ID)


@dataclass(frozen=True, slots=True)
class ExternalActionServiceConfig:
    mode: str = EXTERNAL_ACTION_SERVICE_MODE_DISABLED
    endpoint: str = ""


@dataclass(frozen=True, slots=True)
class ExternalActionServiceReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    api_routes: tuple[str, ...]
    runtime_facade_methods: tuple[str, ...]
    process_split_candidate: bool
    process_split_ready: bool
    state_owner: str
    backend_config_env: str
    dry_run_config_env: str
    endpoint_config_env: str
    endpoint: str
    backend_enabled: bool
    backend_runtime_attr: str
    backend_mode: str
    injected_runtime_backend: bool
    backend_rollback: str
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


ExternalActionBackendFactory = Callable[..., DryRunExternalActionExecutionBackend | HttpExternalActionExecutionBackend]


def _normalized_mode(value: Any) -> str:
    raw = safe_str(value, EXTERNAL_ACTION_SERVICE_MODE_DISABLED).strip().lower()
    if raw in {"dry-run", "dry_run", "enabled", "worker_client", EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE}:
        return EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN
    if raw in {"http", "http_worker", "worker_http", EXTERNAL_ACTION_BACKEND_HTTP_MODE}:
        return EXTERNAL_ACTION_SERVICE_MODE_HTTP
    return EXTERNAL_ACTION_SERVICE_MODE_DISABLED


def external_action_service_config_from_env(env: Mapping[str, str]) -> ExternalActionServiceConfig:
    if as_bool(env.get(EXTERNAL_ACTION_SERVICE_CONFIG_DRY_RUN_ENV), default=False):
        return ExternalActionServiceConfig(mode=EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN)
    return ExternalActionServiceConfig(
        mode=_normalized_mode(env.get(EXTERNAL_ACTION_SERVICE_CONFIG_BACKEND_ENV)),
        endpoint=safe_str(env.get(EXTERNAL_ACTION_SERVICE_CONFIG_ENDPOINT_ENV)).strip(),
    )


class ExternalActionServiceHandle:
    def __init__(
        self,
        config: ExternalActionServiceConfig,
        *,
        backend_factory: ExternalActionBackendFactory = build_external_action_execution_backend,
    ) -> None:
        self.config = config
        self._backend_factory = backend_factory
        self._started = False
        self._backend: DryRunExternalActionExecutionBackend | HttpExternalActionExecutionBackend | None = None
        self._injected_runtime_backend = False
        self._last_readiness = self._readiness(
            started=False,
            ready=False,
            backend_mode=EXTERNAL_ACTION_BACKEND_DISABLED_MODE,
            injected=False,
            notes=("default_disabled_backend",),
        )

    def start(self, runtime: Any) -> ExternalActionServiceReadiness:
        self._started = True
        self._clear_injected_backend(runtime)
        if self.config.mode == EXTERNAL_ACTION_SERVICE_MODE_DISABLED:
            self._backend = None
            self._last_readiness = self._readiness(
                started=True,
                ready=False,
                backend_mode=EXTERNAL_ACTION_BACKEND_DISABLED_MODE,
                injected=False,
                notes=("configured_disabled_backend", "current_routes_use_in_process_facades"),
            )
            return self._last_readiness
        if self.config.mode == EXTERNAL_ACTION_SERVICE_MODE_HTTP and not self.config.endpoint:
            self._backend = None
            self._last_readiness = self._readiness(
                started=True,
                ready=False,
                backend_mode=EXTERNAL_ACTION_BACKEND_DISABLED_MODE,
                injected=False,
                notes=("configured_http_backend_missing_endpoint", "current_routes_use_in_process_facades"),
            )
            return self._last_readiness

        backend_mode = (
            EXTERNAL_ACTION_BACKEND_HTTP_MODE
            if self.config.mode == EXTERNAL_ACTION_SERVICE_MODE_HTTP
            else EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE
        )
        backend = self._backend_factory(
            mode=backend_mode,
            enabled=True,
            endpoint=self.config.endpoint,
        )
        self._backend = backend
        setattr(runtime, EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR, backend)
        self._injected_runtime_backend = True
        self._last_readiness = self._readiness(
            started=True,
            ready=True,
            backend_mode=backend.mode,
            injected=True,
            notes=(
                "dry_run_backend_injected",
                "approved_execution_only",
                "policy_approval_stays_route_owned",
            ),
        )
        return self._last_readiness

    def close(self, runtime: Any) -> ExternalActionServiceReadiness:
        self._clear_injected_backend(runtime)
        self._backend = None
        self._started = False
        self._last_readiness = self._readiness(
            started=False,
            ready=False,
            backend_mode=EXTERNAL_ACTION_BACKEND_DISABLED_MODE,
            injected=False,
            notes=("service_handle_closed", "runtime_backend_attr_cleared"),
        )
        return self._last_readiness

    def readiness(self) -> ExternalActionServiceReadiness:
        return self._last_readiness

    def _clear_injected_backend(self, runtime: Any) -> None:
        current = getattr(runtime, EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR, None)
        if self._injected_runtime_backend and current is self._backend:
            delattr(runtime, EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR)
        self._injected_runtime_backend = False

    def _readiness(
        self,
        *,
        started: bool,
        ready: bool,
        backend_mode: str,
        injected: bool,
        notes: tuple[str, ...],
    ) -> ExternalActionServiceReadiness:
        return ExternalActionServiceReadiness(
            service_id=EXTERNAL_ACTION_SERVICE_ID,
            mode=self.config.mode,
            started=started,
            ready=ready,
            api_routes=EXTERNAL_ACTION_SERVICE_CONTRACT.api_routes,
            runtime_facade_methods=EXTERNAL_ACTION_SERVICE_CONTRACT.runtime_facade_methods,
            process_split_candidate=EXTERNAL_ACTION_SERVICE_CONTRACT.process_split_candidate,
            process_split_ready=EXTERNAL_ACTION_SERVICE_CONTRACT.process_split_ready,
            state_owner=EXTERNAL_ACTION_STATE_OWNER,
            backend_config_env=EXTERNAL_ACTION_SERVICE_CONFIG_BACKEND_ENV,
            dry_run_config_env=EXTERNAL_ACTION_SERVICE_CONFIG_DRY_RUN_ENV,
            endpoint_config_env=EXTERNAL_ACTION_SERVICE_CONFIG_ENDPOINT_ENV,
            endpoint=self.config.endpoint,
            backend_enabled=self.config.mode in {EXTERNAL_ACTION_SERVICE_MODE_DRY_RUN, EXTERNAL_ACTION_SERVICE_MODE_HTTP},
            backend_runtime_attr=EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR,
            backend_mode=backend_mode,
            injected_runtime_backend=injected,
            backend_rollback=EXTERNAL_ACTION_BACKEND_ROLLBACK,
            fallback_adapter=EXTERNAL_ACTION_FALLBACK_ADAPTER,
            rollback=EXTERNAL_ACTION_ROLLBACK,
            notes=notes,
        )


def build_external_action_service_handle(
    config: ExternalActionServiceConfig | None = None,
    *,
    backend_factory: ExternalActionBackendFactory = build_external_action_execution_backend,
) -> ExternalActionServiceHandle:
    return ExternalActionServiceHandle(
        ExternalActionServiceConfig() if config is None else config,
        backend_factory=backend_factory,
    )


def external_action_service_readiness(runtime: Any) -> ExternalActionServiceReadiness:
    handle = getattr(runtime, "_external_action_service", None)
    if handle is None:
        return build_external_action_service_handle().readiness()
    return handle.readiness()
