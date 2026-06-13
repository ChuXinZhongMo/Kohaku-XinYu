from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from xinyu_bridge_codex_execution_backend import (
    CODEX_EXECUTION_BACKEND_RUNTIME_ATTR,
    CODEX_EXECUTION_IN_PROCESS_BACKEND,
)
from xinyu_bridge_codex_execution_contract import (
    CODEX_EXECUTION_FALLBACK_ADAPTER,
    CODEX_EXECUTION_ROLLBACK,
    CODEX_EXECUTION_SERVICE_ID,
    CODEX_EXECUTION_STATE_OWNER,
)
from xinyu_bridge_codex_execution_worker_client import (
    CODEX_EXECUTION_WORKER_CLIENT_MODE,
    DryRunCodexExecutionWorkerClient,
    HttpCodexExecutionWorkerClient,
    build_codex_execution_worker_client,
)
from xinyu_bridge_values import as_bool, as_int, safe_str
from xinyu_serviceization_contracts import service_contract_by_id


CODEX_EXECUTION_SERVICE_MODE_IN_PROCESS = "in_process"
CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT = "worker_client"
CODEX_EXECUTION_SERVICE_CONFIG_BACKEND_ENV = "XINYU_CODEX_EXECUTION_BACKEND"
CODEX_EXECUTION_SERVICE_CONFIG_ENDPOINT_ENV = "XINYU_CODEX_EXECUTION_WORKER_ENDPOINT"
CODEX_EXECUTION_SERVICE_CONFIG_WORKER_ENABLED_ENV = "XINYU_CODEX_EXECUTION_WORKER_ENABLED"
CODEX_EXECUTION_SERVICE_CONFIG_WORKER_HEALTHY_ENV = "XINYU_CODEX_EXECUTION_WORKER_HEALTHY"
CODEX_EXECUTION_SERVICE_CONFIG_FALLBACK_ENV = "XINYU_CODEX_EXECUTION_FALLBACK_ON_UNHEALTHY"
CODEX_EXECUTION_SERVICE_CONFIG_HEALTH_TIMEOUT_ENV = "XINYU_CODEX_EXECUTION_HEALTH_TIMEOUT_SECONDS"
CODEX_EXECUTION_SERVICE_CONFIG_SUBMIT_TIMEOUT_ENV = "XINYU_CODEX_EXECUTION_SUBMIT_TIMEOUT_SECONDS"
CODEX_EXECUTION_SERVICE_CONFIG_CANCEL_TIMEOUT_ENV = "XINYU_CODEX_EXECUTION_CANCEL_TIMEOUT_SECONDS"
CODEX_EXECUTION_SERVICE_DEFAULT_HEALTH_TIMEOUT_SECONDS = 5
CODEX_EXECUTION_SERVICE_DEFAULT_SUBMIT_TIMEOUT_SECONDS = 30
CODEX_EXECUTION_SERVICE_DEFAULT_CANCEL_TIMEOUT_SECONDS = 10
CODEX_EXECUTION_SERVICE_CONTRACT = service_contract_by_id(CODEX_EXECUTION_SERVICE_ID)


@dataclass(frozen=True, slots=True)
class CodexExecutionServiceConfig:
    mode: str = CODEX_EXECUTION_SERVICE_MODE_IN_PROCESS
    endpoint: str = ""
    worker_enabled: bool = False
    worker_healthy: bool = True
    fallback_on_unhealthy: bool = True
    health_timeout_seconds: int = CODEX_EXECUTION_SERVICE_DEFAULT_HEALTH_TIMEOUT_SECONDS
    submit_timeout_seconds: int = CODEX_EXECUTION_SERVICE_DEFAULT_SUBMIT_TIMEOUT_SECONDS
    cancel_timeout_seconds: int = CODEX_EXECUTION_SERVICE_DEFAULT_CANCEL_TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class CodexExecutionServiceReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    process_split_candidate: bool
    process_split_ready: bool
    backend_mode: str
    injected_runtime_backend: bool
    fallback_backend: str
    endpoint: str
    worker_enabled: bool
    worker_healthy: bool
    fallback_on_unhealthy: bool
    health_timeout_seconds: int
    submit_timeout_seconds: int
    cancel_timeout_seconds: int
    api_routes: tuple[str, ...]
    runtime_facade_methods: tuple[str, ...]
    process_split_gate: str
    state_owner: str
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


CodexExecutionWorkerClientFactory = Callable[..., DryRunCodexExecutionWorkerClient | HttpCodexExecutionWorkerClient]


def _normalized_mode(value: Any) -> str:
    raw = safe_str(value, CODEX_EXECUTION_SERVICE_MODE_IN_PROCESS).strip().lower()
    if raw in {"worker", "worker_client", CODEX_EXECUTION_WORKER_CLIENT_MODE}:
        return CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT
    return CODEX_EXECUTION_SERVICE_MODE_IN_PROCESS


def codex_execution_service_config_from_env(env: Mapping[str, str]) -> CodexExecutionServiceConfig:
    return CodexExecutionServiceConfig(
        mode=_normalized_mode(env.get(CODEX_EXECUTION_SERVICE_CONFIG_BACKEND_ENV)),
        endpoint=safe_str(env.get(CODEX_EXECUTION_SERVICE_CONFIG_ENDPOINT_ENV)).strip(),
        worker_enabled=as_bool(env.get(CODEX_EXECUTION_SERVICE_CONFIG_WORKER_ENABLED_ENV), default=False),
        worker_healthy=as_bool(env.get(CODEX_EXECUTION_SERVICE_CONFIG_WORKER_HEALTHY_ENV), default=True),
        fallback_on_unhealthy=as_bool(env.get(CODEX_EXECUTION_SERVICE_CONFIG_FALLBACK_ENV), default=True),
        health_timeout_seconds=max(
            1,
            as_int(
                env.get(CODEX_EXECUTION_SERVICE_CONFIG_HEALTH_TIMEOUT_ENV),
                CODEX_EXECUTION_SERVICE_DEFAULT_HEALTH_TIMEOUT_SECONDS,
            ),
        ),
        submit_timeout_seconds=max(
            1,
            as_int(
                env.get(CODEX_EXECUTION_SERVICE_CONFIG_SUBMIT_TIMEOUT_ENV),
                CODEX_EXECUTION_SERVICE_DEFAULT_SUBMIT_TIMEOUT_SECONDS,
            ),
        ),
        cancel_timeout_seconds=max(
            1,
            as_int(
                env.get(CODEX_EXECUTION_SERVICE_CONFIG_CANCEL_TIMEOUT_ENV),
                CODEX_EXECUTION_SERVICE_DEFAULT_CANCEL_TIMEOUT_SECONDS,
            ),
        ),
    )


class CodexExecutionServiceHandle:
    def __init__(
        self,
        config: CodexExecutionServiceConfig,
        *,
        worker_client_factory: CodexExecutionWorkerClientFactory = build_codex_execution_worker_client,
    ) -> None:
        self.config = config
        self._worker_client_factory = worker_client_factory
        self._started = False
        self._client: DryRunCodexExecutionWorkerClient | HttpCodexExecutionWorkerClient | None = None
        self._injected_runtime_backend = False
        self._last_readiness = self._readiness(
            started=False,
            ready=config.mode == CODEX_EXECUTION_SERVICE_MODE_IN_PROCESS,
            backend_mode=CODEX_EXECUTION_IN_PROCESS_BACKEND,
            injected=False,
            notes=("default_in_process_backend",),
        )

    def start(self, runtime: Any) -> CodexExecutionServiceReadiness:
        self._started = True
        self._clear_injected_backend(runtime)
        if self.config.mode != CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT:
            self._last_readiness = self._readiness(
                started=True,
                ready=True,
                backend_mode=CODEX_EXECUTION_IN_PROCESS_BACKEND,
                injected=False,
                notes=("configured_in_process_backend", "no_external_worker_started"),
            )
            return self._last_readiness

        client = self._worker_client_factory(
            endpoint=self.config.endpoint,
            enabled=self.config.worker_enabled,
            healthy=self.config.worker_healthy,
            health_timeout_seconds=self.config.health_timeout_seconds,
            submit_timeout_seconds=self.config.submit_timeout_seconds,
            cancel_timeout_seconds=self.config.cancel_timeout_seconds,
        )
        self._client = client
        client_readiness = client.readiness()
        if client_readiness.ready:
            setattr(runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR, client)
            self._injected_runtime_backend = True
            self._last_readiness = self._readiness(
                started=True,
                ready=True,
                backend_mode=client.mode,
                injected=True,
                notes=("worker_client_backend_injected", "no_external_worker_started"),
            )
            return self._last_readiness

        ready = self.config.fallback_on_unhealthy
        self._last_readiness = self._readiness(
            started=True,
            ready=ready,
            backend_mode=CODEX_EXECUTION_IN_PROCESS_BACKEND if ready else client.mode,
            injected=False,
            notes=(
                "worker_client_not_ready",
                "fallback_to_in_process_backend" if ready else "fallback_disabled",
                "no_external_worker_started",
            ),
        )
        return self._last_readiness

    def close(self, runtime: Any) -> CodexExecutionServiceReadiness:
        self._clear_injected_backend(runtime)
        close = getattr(self._client, "close", None)
        if callable(close):
            close()
        self._client = None
        self._started = False
        self._last_readiness = self._readiness(
            started=False,
            ready=self.config.mode == CODEX_EXECUTION_SERVICE_MODE_IN_PROCESS,
            backend_mode=CODEX_EXECUTION_IN_PROCESS_BACKEND,
            injected=False,
            notes=("service_handle_closed", "runtime_backend_attr_cleared"),
        )
        return self._last_readiness

    def readiness(self) -> CodexExecutionServiceReadiness:
        return self._last_readiness

    def _clear_injected_backend(self, runtime: Any) -> None:
        current = getattr(runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR, None)
        if self._injected_runtime_backend and current is self._client:
            delattr(runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR)
        self._injected_runtime_backend = False

    def _readiness(
        self,
        *,
        started: bool,
        ready: bool,
        backend_mode: str,
        injected: bool,
        notes: tuple[str, ...],
    ) -> CodexExecutionServiceReadiness:
        return CodexExecutionServiceReadiness(
            service_id=CODEX_EXECUTION_SERVICE_ID,
            mode=self.config.mode,
            started=started,
            ready=ready,
            process_split_candidate=CODEX_EXECUTION_SERVICE_CONTRACT.process_split_candidate,
            process_split_ready=CODEX_EXECUTION_SERVICE_CONTRACT.process_split_ready,
            backend_mode=backend_mode,
            injected_runtime_backend=injected,
            fallback_backend=CODEX_EXECUTION_IN_PROCESS_BACKEND,
            endpoint=self.config.endpoint,
            worker_enabled=self.config.worker_enabled,
            worker_healthy=self.config.worker_healthy,
            fallback_on_unhealthy=self.config.fallback_on_unhealthy,
            health_timeout_seconds=self.config.health_timeout_seconds,
            submit_timeout_seconds=self.config.submit_timeout_seconds,
            cancel_timeout_seconds=self.config.cancel_timeout_seconds,
            api_routes=CODEX_EXECUTION_SERVICE_CONTRACT.api_routes,
            runtime_facade_methods=CODEX_EXECUTION_SERVICE_CONTRACT.runtime_facade_methods,
            process_split_gate=CODEX_EXECUTION_SERVICE_CONTRACT.process_split_gate,
            state_owner=CODEX_EXECUTION_STATE_OWNER,
            fallback_adapter=CODEX_EXECUTION_FALLBACK_ADAPTER,
            rollback=CODEX_EXECUTION_ROLLBACK,
            notes=notes,
        )


def build_codex_execution_service_handle(
    config: CodexExecutionServiceConfig | None = None,
    *,
    worker_client_factory: CodexExecutionWorkerClientFactory = build_codex_execution_worker_client,
) -> CodexExecutionServiceHandle:
    return CodexExecutionServiceHandle(
        CodexExecutionServiceConfig() if config is None else config,
        worker_client_factory=worker_client_factory,
    )


def codex_execution_service_readiness(runtime: Any) -> CodexExecutionServiceReadiness:
    handle = getattr(runtime, "_codex_execution_service", None)
    if handle is None:
        return build_codex_execution_service_handle().readiness()
    return handle.readiness()
