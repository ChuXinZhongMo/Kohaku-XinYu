from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping
from urllib.parse import urlparse

from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_SURFACE_FALLBACK_ADAPTER,
    DESKTOP_SURFACE_ROLLBACK,
)
from xinyu_bridge_desktop_surface_route_backend import (
    DESKTOP_SURFACE_ROUTE_BACKEND_ROLLBACK,
    DESKTOP_SURFACE_SERVICE_ID,
    DesktopSurfaceRouteRequest,
    DesktopSurfaceTransport,
)


DESKTOP_SURFACE_WORKER_SERVICE_MODE = "desktop_surface_route_backend_service_dry_run"
DESKTOP_SURFACE_WORKER_SERVICE_ROUTES = (
    "/health",
    "/desktop-surface/execute",
    "/desktop-surface/executions",
)
DESKTOP_SURFACE_WORKER_SERVICE_ROLLBACK = "stop_desktop_surface_worker_and_unset_route_backend"


@dataclass(frozen=True, slots=True)
class DesktopSurfaceWorkerServiceReadiness:
    service_id: str
    mode: str
    ready: bool
    dry_run: bool
    mutates_state: bool
    owns_websocket_lifecycle: bool
    routes: tuple[str, ...]
    fallback_adapter: str
    rollback: str
    contract_rollback: str
    notes: tuple[str, ...] = ()


class DesktopSurfaceWorkerService:
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = bool(ready)
        self._executions: list[dict[str, Any]] = []

    def readiness(self) -> DesktopSurfaceWorkerServiceReadiness:
        return DesktopSurfaceWorkerServiceReadiness(
            service_id=DESKTOP_SURFACE_SERVICE_ID,
            mode=DESKTOP_SURFACE_WORKER_SERVICE_MODE,
            ready=self.ready,
            dry_run=True,
            mutates_state=False,
            owns_websocket_lifecycle=False,
            routes=DESKTOP_SURFACE_WORKER_SERVICE_ROUTES,
            fallback_adapter=DESKTOP_SURFACE_FALLBACK_ADAPTER,
            rollback=DESKTOP_SURFACE_WORKER_SERVICE_ROLLBACK,
            contract_rollback=DESKTOP_SURFACE_ROLLBACK,
            notes=(
                "dry_run_route_backend_service",
                "desktop_event_stream_ws_lifecycle_remains_app_owned",
                "does_not_mutate_desktop_surface_state",
            ),
        )

    def handle_request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        normalized_method = str(method or "").upper()
        normalized_path = _normalize_path(path)
        request_payload = dict(payload or {})

        if normalized_method == "GET" and normalized_path == "/health":
            readiness = self.readiness()
            return {"ok": readiness.ready, **asdict(readiness)}
        if normalized_method == "POST" and normalized_path == "/desktop-surface/execute":
            return self._execute(request_payload)
        if normalized_method == "GET" and normalized_path == "/desktop-surface/executions":
            return {
                "service_id": DESKTOP_SURFACE_SERVICE_ID,
                "mode": DESKTOP_SURFACE_WORKER_SERVICE_MODE,
                "items": list(self._executions),
            }
        if normalized_path in DESKTOP_SURFACE_WORKER_SERVICE_ROUTES:
            return _error_response("method_not_allowed", http_status=405)
        return _error_response("not_found", http_status=404)

    def _execute(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = desktop_surface_route_request_from_payload(payload)
        request_shape = request.dry_run_shape()
        if not self.ready:
            return {
                "accepted": False,
                "executed": False,
                "service_id": DESKTOP_SURFACE_SERVICE_ID,
                "status": "fallback_required",
                "mode": DESKTOP_SURFACE_WORKER_SERVICE_MODE,
                "dry_run": True,
                "request": request_shape,
                "fallback_adapter": DESKTOP_SURFACE_FALLBACK_ADAPTER,
                "rollback": DESKTOP_SURFACE_ROUTE_BACKEND_ROLLBACK,
                "contract_rollback": DESKTOP_SURFACE_ROLLBACK,
            }
        record = {
            "status": "dry_run_accepted",
            "executed": False,
            "request": request_shape,
        }
        self._executions.append(record)
        return {
            "accepted": True,
            "executed": False,
            "service_id": DESKTOP_SURFACE_SERVICE_ID,
            "status": "dry_run_accepted",
            "mode": DESKTOP_SURFACE_WORKER_SERVICE_MODE,
            "dry_run": True,
            "request": request_shape,
            "fallback_adapter": DESKTOP_SURFACE_FALLBACK_ADAPTER,
            "rollback": DESKTOP_SURFACE_ROUTE_BACKEND_ROLLBACK,
            "contract_rollback": DESKTOP_SURFACE_ROLLBACK,
            "notes": (
                "runtime_method_not_invoked",
                "desktop_event_stream_ws_lifecycle_not_owned",
                "desktop_surface_state_not_mutated",
                "snapshot_dto_shape_remains_fallback_owned",
            ),
        }


def desktop_surface_route_request_from_payload(payload: Mapping[str, Any]) -> DesktopSurfaceRouteRequest:
    nested_payload = payload.get("payload")
    query = payload.get("query")
    return DesktopSurfaceRouteRequest(
        route=str(payload.get("route") or ""),
        http_method=str(payload.get("http_method") or "GET"),
        runtime_method=str(payload.get("runtime_method") or ""),
        payload=dict(nested_payload) if isinstance(nested_payload, Mapping) else {},
        query=dict(query) if isinstance(query, Mapping) else {},
    )


def desktop_surface_worker_service_transport(service: DesktopSurfaceWorkerService) -> DesktopSurfaceTransport:
    def transport(method: str, url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
        del timeout_seconds
        return service.handle_request(method, urlparse(url).path, payload)

    return transport


def _normalize_path(path: str) -> str:
    parsed = urlparse(str(path or ""))
    normalized = parsed.path or "/"
    if normalized != "/" and normalized.endswith("/"):
        return normalized[:-1]
    return normalized


def _error_response(status: str, *, http_status: int) -> dict[str, Any]:
    return {
        "accepted": False,
        "executed": False,
        "service_id": DESKTOP_SURFACE_SERVICE_ID,
        "status": status,
        "http_status": http_status,
    }


__all__ = [
    "DESKTOP_SURFACE_WORKER_SERVICE_MODE",
    "DESKTOP_SURFACE_WORKER_SERVICE_ROUTES",
    "DESKTOP_SURFACE_WORKER_SERVICE_ROLLBACK",
    "DesktopSurfaceWorkerService",
    "DesktopSurfaceWorkerServiceReadiness",
    "desktop_surface_route_request_from_payload",
    "desktop_surface_worker_service_transport",
]
