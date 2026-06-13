from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_SURFACE_FALLBACK_ADAPTER,
    DESKTOP_SURFACE_ROLLBACK,
    DESKTOP_SURFACE_STATE_OWNER,
    DesktopEventStreamReadiness,
    desktop_event_stream_readiness,
)
from xinyu_bridge_desktop_surface_route_backend import (
    DESKTOP_SURFACE_BACKEND_DISABLED_MODE,
    DESKTOP_SURFACE_BACKEND_DRY_RUN_MODE,
    DESKTOP_SURFACE_BACKEND_HTTP_MODE,
    DESKTOP_SURFACE_ROUTE_BACKEND_ROLLBACK,
    DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR,
    DESKTOP_SURFACE_SERVICE_ID,
    DryRunDesktopSurfaceRouteBackend,
    HttpDesktopSurfaceRouteBackend,
    build_desktop_surface_route_backend,
)
from xinyu_bridge_values import as_bool, safe_str
from xinyu_serviceization_contracts import service_contract_by_id


DESKTOP_SURFACE_SERVICE_MODE_IN_PROCESS = "in_process"
DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND = "dry_run_route_backend"
DESKTOP_SURFACE_SERVICE_MODE_HTTP_ROUTE_BACKEND = "http_route_backend"
DESKTOP_SURFACE_SERVICE_CONFIG_BACKEND_ENV = "XINYU_DESKTOP_SURFACE_BACKEND"
DESKTOP_SURFACE_SERVICE_CONFIG_ROUTE_BACKEND_ENV = "XINYU_DESKTOP_SURFACE_ROUTE_BACKEND_ENABLED"
DESKTOP_SURFACE_SERVICE_CONFIG_ENDPOINT_ENV = "XINYU_DESKTOP_SURFACE_ROUTE_BACKEND_ENDPOINT"
DESKTOP_SURFACE_SERVICE_CONTRACT = service_contract_by_id(DESKTOP_SURFACE_SERVICE_ID)


@dataclass(frozen=True, slots=True)
class DesktopSurfaceServiceConfig:
    mode: str = DESKTOP_SURFACE_SERVICE_MODE_IN_PROCESS
    endpoint: str = ""


@dataclass(frozen=True, slots=True)
class DesktopSurfaceServiceReadiness:
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
    event_stream: DesktopEventStreamReadiness
    backend: str
    backend_config_env: str
    route_backend_config_env: str
    endpoint_config_env: str
    endpoint: str
    route_backend_enabled: bool
    route_backend_runtime_attr: str
    route_backend_mode: str
    route_backend_injected: bool
    notes: tuple[str, ...] = ()


DesktopSurfaceRouteBackendFactory = Callable[..., DryRunDesktopSurfaceRouteBackend | HttpDesktopSurfaceRouteBackend]


def _normalized_mode(value: Any) -> str:
    raw = safe_str(value, DESKTOP_SURFACE_SERVICE_MODE_IN_PROCESS).strip().lower()
    if raw in {"dry-run", "dry_run", "route_backend", "dry_run_route_backend", DESKTOP_SURFACE_BACKEND_DRY_RUN_MODE}:
        return DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND
    if raw in {"http", "http_route_backend", "route_backend_http", DESKTOP_SURFACE_BACKEND_HTTP_MODE}:
        return DESKTOP_SURFACE_SERVICE_MODE_HTTP_ROUTE_BACKEND
    return DESKTOP_SURFACE_SERVICE_MODE_IN_PROCESS


def desktop_surface_service_config_from_env(env: Mapping[str, str]) -> DesktopSurfaceServiceConfig:
    if as_bool(env.get(DESKTOP_SURFACE_SERVICE_CONFIG_ROUTE_BACKEND_ENV), default=False):
        return DesktopSurfaceServiceConfig(mode=DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND)
    return DesktopSurfaceServiceConfig(
        mode=_normalized_mode(env.get(DESKTOP_SURFACE_SERVICE_CONFIG_BACKEND_ENV)),
        endpoint=safe_str(env.get(DESKTOP_SURFACE_SERVICE_CONFIG_ENDPOINT_ENV)).strip(),
    )


class DesktopSurfaceServiceHandle:
    def __init__(
        self,
        config: DesktopSurfaceServiceConfig,
        *,
        route_backend_factory: DesktopSurfaceRouteBackendFactory = build_desktop_surface_route_backend,
    ) -> None:
        self.config = config
        self._route_backend_factory = route_backend_factory
        self._started = False
        self._runtime: Any | None = None
        self._route_backend: DryRunDesktopSurfaceRouteBackend | HttpDesktopSurfaceRouteBackend | None = None
        self._injected_route_backend = False

    def start(self, runtime: Any) -> DesktopSurfaceServiceReadiness:
        self._started = True
        self._runtime = runtime
        self._clear_injected_backend(runtime)
        if self.config.mode == DESKTOP_SURFACE_SERVICE_MODE_HTTP_ROUTE_BACKEND and not self.config.endpoint:
            self._route_backend = None
        elif self.config.mode in {
            DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
            DESKTOP_SURFACE_SERVICE_MODE_HTTP_ROUTE_BACKEND,
        }:
            backend_mode = (
                DESKTOP_SURFACE_BACKEND_HTTP_MODE
                if self.config.mode == DESKTOP_SURFACE_SERVICE_MODE_HTTP_ROUTE_BACKEND
                else DESKTOP_SURFACE_BACKEND_DRY_RUN_MODE
            )
            backend = self._route_backend_factory(
                mode=backend_mode,
                enabled=True,
                endpoint=self.config.endpoint,
            )
            self._route_backend = backend
            setattr(runtime, DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR, backend)
            self._injected_route_backend = True
        else:
            self._route_backend = None
        return self.readiness(runtime)

    def close(self, runtime: Any) -> DesktopSurfaceServiceReadiness:
        self._clear_injected_backend(runtime)
        self._route_backend = None
        self._started = False
        readiness = self.readiness(runtime)
        self._runtime = None
        return readiness

    def readiness(self, runtime: Any | None = None) -> DesktopSurfaceServiceReadiness:
        bound_runtime = runtime if runtime is not None else self._runtime
        event_stream = desktop_event_stream_readiness(
            event_bus=getattr(bound_runtime, "desktop_event_bus", None),
            ws_server=getattr(bound_runtime, "desktop_ws_server", None),
        )
        route_backend_mode = (
            getattr(self._route_backend, "mode", DESKTOP_SURFACE_BACKEND_DISABLED_MODE)
            if self._injected_route_backend
            else DESKTOP_SURFACE_BACKEND_DISABLED_MODE
        )
        return DesktopSurfaceServiceReadiness(
            service_id=DESKTOP_SURFACE_SERVICE_ID,
            mode=self.config.mode,
            started=self._started,
            ready=self._started
            and not (
                self.config.mode == DESKTOP_SURFACE_SERVICE_MODE_HTTP_ROUTE_BACKEND
                and not self.config.endpoint
            ),
            api_routes=DESKTOP_SURFACE_SERVICE_CONTRACT.api_routes,
            runtime_facade_methods=DESKTOP_SURFACE_SERVICE_CONTRACT.runtime_facade_methods,
            process_split_candidate=DESKTOP_SURFACE_SERVICE_CONTRACT.process_split_candidate,
            process_split_ready=DESKTOP_SURFACE_SERVICE_CONTRACT.process_split_ready,
            state_owner=DESKTOP_SURFACE_STATE_OWNER,
            fallback_adapter=DESKTOP_SURFACE_FALLBACK_ADAPTER,
            rollback=DESKTOP_SURFACE_ROLLBACK,
            event_stream=event_stream,
            backend=route_backend_mode,
            backend_config_env=DESKTOP_SURFACE_SERVICE_CONFIG_BACKEND_ENV,
            route_backend_config_env=DESKTOP_SURFACE_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
            endpoint_config_env=DESKTOP_SURFACE_SERVICE_CONFIG_ENDPOINT_ENV,
            endpoint=self.config.endpoint,
            route_backend_enabled=self.config.mode in {
                DESKTOP_SURFACE_SERVICE_MODE_DRY_RUN_ROUTE_BACKEND,
                DESKTOP_SURFACE_SERVICE_MODE_HTTP_ROUTE_BACKEND,
            },
            route_backend_runtime_attr=DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR,
            route_backend_mode=route_backend_mode,
            route_backend_injected=self._injected_route_backend,
            notes=(
                "runtime_desktop_surface_service",
                f"event_stream_{event_stream.status}",
                "http_route_backend_endpoint_missing"
                if self.config.mode == DESKTOP_SURFACE_SERVICE_MODE_HTTP_ROUTE_BACKEND and not self.config.endpoint
                else "route_backend_endpoint_configured"
                if self.config.mode == DESKTOP_SURFACE_SERVICE_MODE_HTTP_ROUTE_BACKEND
                else "route_backend_endpoint_not_required",
                f"route_backend_rollback={DESKTOP_SURFACE_ROUTE_BACKEND_ROLLBACK}",
            ),
        )

    def _clear_injected_backend(self, runtime: Any) -> None:
        current = getattr(runtime, DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR, None)
        if self._injected_route_backend and current is self._route_backend:
            delattr(runtime, DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR)
        self._injected_route_backend = False


def build_desktop_surface_service_handle(
    config: DesktopSurfaceServiceConfig | None = None,
    *,
    route_backend_factory: DesktopSurfaceRouteBackendFactory = build_desktop_surface_route_backend,
) -> DesktopSurfaceServiceHandle:
    return DesktopSurfaceServiceHandle(
        DesktopSurfaceServiceConfig() if config is None else config,
        route_backend_factory=route_backend_factory,
    )


def desktop_surface_service_readiness(runtime: Any) -> DesktopSurfaceServiceReadiness:
    handle = getattr(runtime, "_desktop_surface_service", None)
    if handle is None:
        return build_desktop_surface_service_handle().readiness(runtime)
    return handle.readiness(runtime)
