from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from xinyu_bridge_desktop_surface_route_backend import (
    DESKTOP_SURFACE_BACKEND_HTTP_MODE,
    DesktopSurfaceRouteRequest,
    HttpDesktopSurfaceRouteBackend,
)
from xinyu_bridge_desktop_surface_worker_service import (
    DESKTOP_SURFACE_WORKER_SERVICE_MODE,
    DESKTOP_SURFACE_WORKER_SERVICE_ROUTES,
    DesktopSurfaceWorkerService,
    desktop_surface_route_request_from_payload,
    desktop_surface_worker_service_transport,
)


def _runtime(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        xinyu_dir=root,
        desktop_snapshot=lambda payload: {"snapshot": payload},
    )


def _request() -> DesktopSurfaceRouteRequest:
    return DesktopSurfaceRouteRequest(
        route="/desktop/snapshot",
        http_method="GET",
        runtime_method="desktop_snapshot",
        payload={"query": {"trace": "dry-run"}},
        query={"trace": "dry-run"},
    )


def test_desktop_surface_worker_service_readiness_is_dry_run_and_ws_safe() -> None:
    readiness = DesktopSurfaceWorkerService().readiness()

    assert readiness.service_id == "desktop_surface"
    assert readiness.mode == DESKTOP_SURFACE_WORKER_SERVICE_MODE
    assert readiness.ready is True
    assert readiness.dry_run is True
    assert readiness.mutates_state is False
    assert readiness.owns_websocket_lifecycle is False
    assert readiness.routes == DESKTOP_SURFACE_WORKER_SERVICE_ROUTES
    assert "desktop_event_stream_ws_lifecycle_remains_app_owned" in readiness.notes


def test_desktop_surface_worker_service_health_route_exposes_readiness_payload() -> None:
    health = DesktopSurfaceWorkerService().handle_request("GET", "/health")

    assert health["ok"] is True
    assert health["service_id"] == "desktop_surface"
    assert health["mode"] == DESKTOP_SURFACE_WORKER_SERVICE_MODE
    assert tuple(health["routes"]) == DESKTOP_SURFACE_WORKER_SERVICE_ROUTES
    assert health["owns_websocket_lifecycle"] is False


def test_desktop_surface_worker_service_execute_records_dry_run_only() -> None:
    service = DesktopSurfaceWorkerService()

    result = service.handle_request("POST", "/desktop-surface/execute", _request().dry_run_shape())
    executions = service.handle_request("GET", "/desktop-surface/executions")

    assert result["accepted"] is True
    assert result["executed"] is False
    assert result["dry_run"] is True
    assert result["mode"] == DESKTOP_SURFACE_WORKER_SERVICE_MODE
    assert result["request"] == _request().dry_run_shape()
    assert "desktop_event_stream_ws_lifecycle_not_owned" in result["notes"]
    assert executions["items"] == [
        {
            "status": "dry_run_accepted",
            "executed": False,
            "request": _request().dry_run_shape(),
        }
    ]


def test_desktop_surface_worker_service_transport_connects_http_backend(tmp_path: Path) -> None:
    service = DesktopSurfaceWorkerService()
    backend = HttpDesktopSurfaceRouteBackend(
        endpoint="http://127.0.0.1:8790/",
        enabled=True,
        transport=desktop_surface_worker_service_transport(service),
    )

    response = asyncio.run(backend.execute(_runtime(tmp_path), _request()))

    assert response["service_id"] == "desktop_surface"
    assert response["mode"] == DESKTOP_SURFACE_BACKEND_HTTP_MODE
    assert response["dry_run"] is False
    assert response["executed"] is False
    assert response["status"] == "dry_run_accepted"
    assert response["worker_response"]["dry_run"] is True
    assert response["worker_response"]["executed"] is False


def test_desktop_surface_worker_service_not_ready_requests_fallback() -> None:
    result = DesktopSurfaceWorkerService(ready=False).handle_request(
        "POST",
        "/desktop-surface/execute",
        _request().dry_run_shape(),
    )

    assert result["accepted"] is False
    assert result["executed"] is False
    assert result["status"] == "fallback_required"
    assert result["fallback_adapter"] == "in_process_runtime_desktop_surface_methods"


def test_desktop_surface_worker_service_rejects_unknown_or_invalid_routes() -> None:
    service = DesktopSurfaceWorkerService()

    assert service.handle_request("GET", "/missing")["http_status"] == 404
    assert service.handle_request("GET", "/desktop-surface/execute")["http_status"] == 405


def test_desktop_surface_route_request_from_payload_uses_safe_defaults() -> None:
    request = desktop_surface_route_request_from_payload({"payload": {"view": "full"}})

    assert request.route == ""
    assert request.http_method == "GET"
    assert request.runtime_method == ""
    assert request.payload == {"view": "full"}
    assert request.query == {}
