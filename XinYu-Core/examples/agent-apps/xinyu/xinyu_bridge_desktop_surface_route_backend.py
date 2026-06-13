from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_SURFACE_FALLBACK_ADAPTER,
    DESKTOP_SURFACE_ROLLBACK,
    DESKTOP_SURFACE_STATE_OWNER,
)


DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR = "_desktop_surface_route_backend"
DESKTOP_SURFACE_SERVICE_ID = "desktop_surface"
DESKTOP_SURFACE_BACKEND_DISABLED_MODE = "disabled_contract_only_route_backend"
DESKTOP_SURFACE_BACKEND_DRY_RUN_MODE = "desktop_surface_route_backend_dry_run"
DESKTOP_SURFACE_BACKEND_HTTP_MODE = "desktop_surface_route_backend_http"
DESKTOP_SURFACE_ROUTE_BACKEND_ROLLBACK = "remove_runtime_backend_attr_to_use_current_desktop_surface_facades"


@dataclass(frozen=True, slots=True)
class DesktopSurfaceRouteRequest:
    route: str
    http_method: str
    runtime_method: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    query: Mapping[str, Any] = field(default_factory=dict)

    def dry_run_shape(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "http_method": self.http_method,
            "runtime_method": self.runtime_method,
            "payload": dict(self.payload),
            "query": dict(self.query),
        }


class DesktopSurfaceRouteBackend(Protocol):
    mode: str

    async def execute(self, runtime: Any, request: DesktopSurfaceRouteRequest) -> dict[str, Any]:
        ...


@dataclass(frozen=True, slots=True)
class DesktopSurfaceRouteBackendReadiness:
    service_id: str
    mode: str
    ready: bool
    runtime_attr: str
    state_owner: str
    fallback_adapter: str
    rollback: str
    contract_rollback: str
    notes: tuple[str, ...] = ()


class DryRunDesktopSurfaceRouteBackend:
    def __init__(self, *, enabled: bool = False, endpoint: str = "", timeout_seconds: int = 30, mode: str = "") -> None:
        del endpoint, timeout_seconds, mode
        self.enabled = bool(enabled)
        self.mode = DESKTOP_SURFACE_BACKEND_DRY_RUN_MODE if self.enabled else DESKTOP_SURFACE_BACKEND_DISABLED_MODE

    async def execute(self, runtime: Any, request: DesktopSurfaceRouteRequest) -> dict[str, Any]:
        runtime_facade_present = hasattr(runtime, request.runtime_method)
        status = "dry_run_ready" if self.enabled else "backend_disabled"
        return {
            "service_id": DESKTOP_SURFACE_SERVICE_ID,
            "status": status,
            "mode": self.mode,
            "enabled": self.enabled,
            "dry_run": True,
            "executed": False,
            "request": request.dry_run_shape(),
            "runtime_facade_present": runtime_facade_present,
            "fallback_adapter": DESKTOP_SURFACE_FALLBACK_ADAPTER,
            "fallback_runtime_method": request.runtime_method,
            "fallback_runtime_facades": "current_in_process_desktop_surface_facades",
            "rollback": DESKTOP_SURFACE_ROUTE_BACKEND_ROLLBACK,
            "contract_rollback": DESKTOP_SURFACE_ROLLBACK,
            "notes": (
                "contract_only_no_desktop_surface_state_mutated",
                "runtime_method_not_invoked",
                "current_in_process_facades_remain_fallback",
                "future_enabled_backend_must_preserve_snapshot_dto_shape",
            ),
        }


DesktopSurfaceTransport = Callable[[str, str, dict[str, Any], int], dict[str, Any]]


class HttpDesktopSurfaceRouteBackend:
    mode = DESKTOP_SURFACE_BACKEND_HTTP_MODE

    def __init__(
        self,
        *,
        endpoint: str,
        enabled: bool = False,
        timeout_seconds: int = 30,
        transport: DesktopSurfaceTransport | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.enabled = bool(enabled)
        self.timeout_seconds = timeout_seconds
        self._transport = _default_json_transport if transport is None else transport

    async def execute(self, runtime: Any, request: DesktopSurfaceRouteRequest) -> dict[str, Any]:
        runtime_facade_present = hasattr(runtime, request.runtime_method)
        if not self.enabled or not self.endpoint:
            return _desktop_surface_backend_response(
                mode=self.mode,
                enabled=self.enabled,
                executed=False,
                status="backend_disabled",
                dry_run=False,
                request=request,
                runtime_facade_present=runtime_facade_present,
            )
        response = self._transport(
            "POST",
            f"{self.endpoint}/desktop-surface/execute",
            request.dry_run_shape(),
            self.timeout_seconds,
        )
        return _desktop_surface_backend_response(
            mode=self.mode,
            enabled=self.enabled,
            executed=bool(response.get("executed", response.get("accepted", False))),
            status=str(response.get("status") or "accepted"),
            dry_run=False,
            request=request,
            runtime_facade_present=runtime_facade_present,
            response=dict(response),
        )


def build_desktop_surface_route_backend(
    *,
    mode: str = DESKTOP_SURFACE_BACKEND_DISABLED_MODE,
    enabled: bool = False,
    endpoint: str = "",
    timeout_seconds: int = 30,
    transport: DesktopSurfaceTransport | None = None,
) -> DryRunDesktopSurfaceRouteBackend | HttpDesktopSurfaceRouteBackend:
    if mode == DESKTOP_SURFACE_BACKEND_HTTP_MODE or endpoint.strip():
        return HttpDesktopSurfaceRouteBackend(
            endpoint=endpoint,
            enabled=enabled,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
    return DryRunDesktopSurfaceRouteBackend(enabled=enabled)


DISABLED_DESKTOP_SURFACE_ROUTE_BACKEND = DryRunDesktopSurfaceRouteBackend(enabled=False)


def desktop_surface_route_backend_for_runtime(
    runtime: Any,
    *,
    explicit_backend: DesktopSurfaceRouteBackend | None = None,
) -> DesktopSurfaceRouteBackend:
    if explicit_backend is not None:
        return explicit_backend
    runtime_backend = getattr(runtime, DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR, None)
    if runtime_backend is not None:
        return runtime_backend
    return DISABLED_DESKTOP_SURFACE_ROUTE_BACKEND


def desktop_surface_route_backend_readiness(
    runtime: Any,
    *,
    explicit_backend: DesktopSurfaceRouteBackend | None = None,
) -> DesktopSurfaceRouteBackendReadiness:
    backend = desktop_surface_route_backend_for_runtime(runtime, explicit_backend=explicit_backend)
    return DesktopSurfaceRouteBackendReadiness(
        service_id=DESKTOP_SURFACE_SERVICE_ID,
        mode=getattr(backend, "mode", type(backend).__name__),
        ready=False,
        runtime_attr=DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR,
        state_owner=DESKTOP_SURFACE_STATE_OWNER,
        fallback_adapter=DESKTOP_SURFACE_FALLBACK_ADAPTER,
        rollback=DESKTOP_SURFACE_ROUTE_BACKEND_ROLLBACK,
        contract_rollback=DESKTOP_SURFACE_ROLLBACK,
        notes=(
            "disabled_by_default_contract_only",
            "dry_run_only_until_desktop_surface_state_store_is_connected",
            "fallback_to_current_in_process_desktop_surface_facades",
        ),
    )


async def maybe_execute_desktop_surface_backend(
    runtime: Any,
    payload: dict[str, Any] | None,
    *,
    route: str,
    http_method: str,
    runtime_method: str,
) -> dict[str, Any] | None:
    if getattr(runtime, "_closed", False):
        return None
    request = _request_from_payload(payload, route=route, http_method=http_method, runtime_method=runtime_method)
    if request is None:
        return None
    backend = desktop_surface_route_backend_for_runtime(runtime)
    if not bool(getattr(backend, "enabled", False)):
        return None
    return await backend.execute(runtime, request)


def _request_from_payload(
    payload: dict[str, Any] | None,
    *,
    route: str,
    http_method: str,
    runtime_method: str,
) -> DesktopSurfaceRouteRequest | None:
    if payload is not None and not isinstance(payload, dict):
        return None
    return DesktopSurfaceRouteRequest(
        route=route,
        http_method=http_method,
        runtime_method=runtime_method,
        payload=dict(payload or {}),
        query=_query_from_payload(payload),
    )


def _query_from_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    query = payload.get("query")
    return dict(query) if isinstance(query, Mapping) else {}


def _desktop_surface_backend_response(
    *,
    mode: str,
    enabled: bool,
    executed: bool,
    status: str,
    dry_run: bool,
    request: DesktopSurfaceRouteRequest,
    runtime_facade_present: bool,
    response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "service_id": DESKTOP_SURFACE_SERVICE_ID,
        "status": status,
        "mode": mode,
        "enabled": enabled,
        "dry_run": dry_run,
        "executed": executed,
        "request": request.dry_run_shape(),
        "runtime_facade_present": runtime_facade_present,
        "fallback_adapter": DESKTOP_SURFACE_FALLBACK_ADAPTER,
        "fallback_runtime_method": request.runtime_method,
        "fallback_runtime_facades": "current_in_process_desktop_surface_facades",
        "rollback": DESKTOP_SURFACE_ROUTE_BACKEND_ROLLBACK,
        "contract_rollback": DESKTOP_SURFACE_ROLLBACK,
        "worker_response": dict(response or {}),
        "notes": (
            "approved_route_request_only",
            "current_in_process_facades_remain_fallback",
            "future_enabled_backend_must_preserve_snapshot_dto_shape",
        ),
    }


def _default_json_transport(method: str, url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except URLError as exc:
        return {"accepted": False, "status": "transport_error", "error": str(exc)}
    if not body.strip():
        return {"accepted": True, "status": "accepted"}
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {"accepted": False, "status": "invalid_worker_response"}
    return parsed if isinstance(parsed, dict) else {"accepted": False, "status": "invalid_worker_response"}
