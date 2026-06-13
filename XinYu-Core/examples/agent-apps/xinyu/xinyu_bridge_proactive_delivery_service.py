from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from xinyu_bridge_proactive_delivery_contract import (
    PROACTIVE_DELIVERY_FALLBACK_ADAPTER,
    PROACTIVE_DELIVERY_ROLLBACK,
    PROACTIVE_DELIVERY_STATE_OWNER,
    proactive_transport_preflight_contract,
)
from xinyu_bridge_proactive_delivery_route_backend import (
    PROACTIVE_DELIVERY_BACKEND_DISABLED_MODE,
    PROACTIVE_DELIVERY_BACKEND_DRY_RUN_MODE,
    PROACTIVE_DELIVERY_BACKEND_HTTP_MODE,
    PROACTIVE_DELIVERY_ROUTE_BACKEND_ROLLBACK,
    PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR,
    PROACTIVE_DELIVERY_SERVICE_ID,
    DryRunProactiveDeliveryRouteBackend,
    HttpProactiveDeliveryRouteBackend,
    build_proactive_delivery_route_backend,
)
from xinyu_bridge_values import as_bool, safe_str
from xinyu_serviceization_contracts import service_contract_by_id


PROACTIVE_DELIVERY_SERVICE_MODE_IN_PROCESS = "in_process"
PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND = "dry_run_route_backend"
PROACTIVE_DELIVERY_SERVICE_MODE_HTTP_ROUTE_BACKEND = "http_route_backend"
PROACTIVE_DELIVERY_SERVICE_CONFIG_BACKEND_ENV = "XINYU_PROACTIVE_DELIVERY_BACKEND"
PROACTIVE_DELIVERY_SERVICE_CONFIG_ROUTE_BACKEND_ENV = "XINYU_PROACTIVE_DELIVERY_ROUTE_BACKEND_ENABLED"
PROACTIVE_DELIVERY_SERVICE_CONFIG_ENDPOINT_ENV = "XINYU_PROACTIVE_DELIVERY_ROUTE_BACKEND_ENDPOINT"


@dataclass(frozen=True, slots=True)
class ProactiveDeliveryServiceConfig:
    mode: str = PROACTIVE_DELIVERY_SERVICE_MODE_IN_PROCESS
    endpoint: str = ""


@dataclass(frozen=True, slots=True)
class ProactiveDeliveryServiceReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    api_routes: tuple[str, ...]
    runtime_facade_methods: tuple[str, ...]
    process_split_candidate: bool
    process_split_ready: bool
    state_owner: str
    fallback_adapter: str
    rollback: str
    backend_config_env: str
    route_backend_config_env: str
    endpoint_config_env: str
    endpoint: str
    route_backend_enabled: bool
    route_backend_runtime_attr: str
    route_backend_mode: str
    route_backend_injected: bool
    transport_preflight_ready: bool
    notes: tuple[str, ...] = ()


ProactiveDeliveryRouteBackendFactory = Callable[..., DryRunProactiveDeliveryRouteBackend | HttpProactiveDeliveryRouteBackend]


def _normalized_mode(value: Any) -> str:
    raw = safe_str(value, PROACTIVE_DELIVERY_SERVICE_MODE_IN_PROCESS).strip().lower()
    if raw in {"dry-run", "dry_run", "route_backend", "dry_run_route_backend", PROACTIVE_DELIVERY_BACKEND_DRY_RUN_MODE}:
        return PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    if raw in {"http", "http_route_backend", "route_backend_http", PROACTIVE_DELIVERY_BACKEND_HTTP_MODE}:
        return PROACTIVE_DELIVERY_SERVICE_MODE_HTTP_ROUTE_BACKEND
    return PROACTIVE_DELIVERY_SERVICE_MODE_IN_PROCESS


def proactive_delivery_service_config_from_env(env: Mapping[str, str]) -> ProactiveDeliveryServiceConfig:
    if as_bool(env.get(PROACTIVE_DELIVERY_SERVICE_CONFIG_ROUTE_BACKEND_ENV), default=False):
        return ProactiveDeliveryServiceConfig(mode=PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    return ProactiveDeliveryServiceConfig(
        mode=_normalized_mode(env.get(PROACTIVE_DELIVERY_SERVICE_CONFIG_BACKEND_ENV)),
        endpoint=safe_str(env.get(PROACTIVE_DELIVERY_SERVICE_CONFIG_ENDPOINT_ENV)).strip(),
    )


class ProactiveDeliveryServiceHandle:
    def __init__(
        self,
        config: ProactiveDeliveryServiceConfig,
        *,
        route_backend_factory: ProactiveDeliveryRouteBackendFactory = build_proactive_delivery_route_backend,
    ) -> None:
        self.config = config
        self._route_backend_factory = route_backend_factory
        self._started = False
        self._route_backend: DryRunProactiveDeliveryRouteBackend | HttpProactiveDeliveryRouteBackend | None = None
        self._injected_route_backend = False

    def start(self, runtime: Any) -> ProactiveDeliveryServiceReadiness:
        self._started = True
        self._clear_injected_backend(runtime)
        if self.config.mode == PROACTIVE_DELIVERY_SERVICE_MODE_HTTP_ROUTE_BACKEND and not self.config.endpoint:
            self._route_backend = None
            return self.readiness()
        if self.config.mode in {
            PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
            PROACTIVE_DELIVERY_SERVICE_MODE_HTTP_ROUTE_BACKEND,
        }:
            backend_mode = (
                PROACTIVE_DELIVERY_BACKEND_HTTP_MODE
                if self.config.mode == PROACTIVE_DELIVERY_SERVICE_MODE_HTTP_ROUTE_BACKEND
                else PROACTIVE_DELIVERY_BACKEND_DRY_RUN_MODE
            )
            backend = self._route_backend_factory(
                mode=backend_mode,
                enabled=True,
                endpoint=self.config.endpoint,
            )
            self._route_backend = backend
            setattr(runtime, PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR, backend)
            self._injected_route_backend = True
        else:
            self._route_backend = None
        return self.readiness()

    def close(self, runtime: Any) -> ProactiveDeliveryServiceReadiness:
        self._clear_injected_backend(runtime)
        self._route_backend = None
        self._started = False
        return self.readiness()

    def readiness(self) -> ProactiveDeliveryServiceReadiness:
        contract = service_contract_by_id(PROACTIVE_DELIVERY_SERVICE_ID)
        transport = proactive_transport_preflight_contract()
        route_backend_mode = (
            getattr(self._route_backend, "mode", PROACTIVE_DELIVERY_BACKEND_DISABLED_MODE)
            if self._injected_route_backend
            else PROACTIVE_DELIVERY_BACKEND_DISABLED_MODE
        )
        return ProactiveDeliveryServiceReadiness(
            service_id=PROACTIVE_DELIVERY_SERVICE_ID,
            mode=self.config.mode,
            started=self._started,
            ready=self._started
            and not (
                self.config.mode == PROACTIVE_DELIVERY_SERVICE_MODE_HTTP_ROUTE_BACKEND
                and not self.config.endpoint
            ),
            api_routes=contract.api_routes,
            runtime_facade_methods=contract.runtime_facade_methods,
            process_split_candidate=contract.process_split_candidate,
            process_split_ready=contract.process_split_ready,
            state_owner=PROACTIVE_DELIVERY_STATE_OWNER,
            fallback_adapter=PROACTIVE_DELIVERY_FALLBACK_ADAPTER,
            rollback=PROACTIVE_DELIVERY_ROLLBACK,
            backend_config_env=PROACTIVE_DELIVERY_SERVICE_CONFIG_BACKEND_ENV,
            route_backend_config_env=PROACTIVE_DELIVERY_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
            endpoint_config_env=PROACTIVE_DELIVERY_SERVICE_CONFIG_ENDPOINT_ENV,
            endpoint=self.config.endpoint,
            route_backend_enabled=self.config.mode in {
                PROACTIVE_DELIVERY_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
                PROACTIVE_DELIVERY_SERVICE_MODE_HTTP_ROUTE_BACKEND,
            },
            route_backend_runtime_attr=PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR,
            route_backend_mode=route_backend_mode,
            route_backend_injected=self._injected_route_backend,
            transport_preflight_ready=transport.ready,
            notes=(
                "runtime_proactive_delivery_service",
                "transport_preflight_ready" if transport.ready else "transport_preflight_not_ready",
                "http_route_backend_endpoint_missing"
                if self.config.mode == PROACTIVE_DELIVERY_SERVICE_MODE_HTTP_ROUTE_BACKEND and not self.config.endpoint
                else "route_backend_endpoint_configured"
                if self.config.mode == PROACTIVE_DELIVERY_SERVICE_MODE_HTTP_ROUTE_BACKEND
                else "route_backend_endpoint_not_required",
                f"route_backend_rollback={PROACTIVE_DELIVERY_ROUTE_BACKEND_ROLLBACK}",
            ),
        )

    def _clear_injected_backend(self, runtime: Any) -> None:
        current = getattr(runtime, PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR, None)
        if self._injected_route_backend and current is self._route_backend:
            delattr(runtime, PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR)
        self._injected_route_backend = False


def build_proactive_delivery_service_handle(
    config: ProactiveDeliveryServiceConfig | None = None,
    *,
    route_backend_factory: ProactiveDeliveryRouteBackendFactory = build_proactive_delivery_route_backend,
) -> ProactiveDeliveryServiceHandle:
    return ProactiveDeliveryServiceHandle(
        ProactiveDeliveryServiceConfig() if config is None else config,
        route_backend_factory=route_backend_factory,
    )


def proactive_delivery_service_readiness(runtime: Any) -> ProactiveDeliveryServiceReadiness:
    handle = getattr(runtime, "_proactive_delivery_service", None)
    if handle is None:
        return build_proactive_delivery_service_handle().readiness()
    return handle.readiness()
