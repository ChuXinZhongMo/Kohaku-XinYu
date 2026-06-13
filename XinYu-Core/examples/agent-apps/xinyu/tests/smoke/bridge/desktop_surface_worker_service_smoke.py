from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[3]
ROOT_TEXT = str(ROOT)
if ROOT_TEXT not in sys.path:
    sys.path.insert(0, ROOT_TEXT)

from xinyu_bridge_desktop_surface_route_backend import DesktopSurfaceRouteRequest, HttpDesktopSurfaceRouteBackend
from xinyu_bridge_desktop_surface_worker_service import (
    DESKTOP_SURFACE_WORKER_SERVICE_MODE,
    DesktopSurfaceWorkerService,
    desktop_surface_worker_service_transport,
)


def _run_smoke() -> None:
    service = DesktopSurfaceWorkerService()
    health = service.handle_request("GET", "/health")
    assert health["ok"] is True, "desktop surface worker service health is not ready"
    assert health["mode"] == DESKTOP_SURFACE_WORKER_SERVICE_MODE, "worker service mode changed"
    assert health["owns_websocket_lifecycle"] is False, "worker service must not own websocket lifecycle"

    backend = HttpDesktopSurfaceRouteBackend(
        endpoint="http://127.0.0.1:8790",
        enabled=True,
        transport=desktop_surface_worker_service_transport(service),
    )
    request = DesktopSurfaceRouteRequest(
        route="/desktop/snapshot",
        http_method="GET",
        runtime_method="desktop_snapshot",
        payload={"view": "full"},
    )
    result = asyncio.run(backend.execute(SimpleNamespace(desktop_snapshot=lambda payload: payload), request))

    assert result["status"] == "dry_run_accepted", "worker service did not accept route request"
    assert result["executed"] is False, "dry-run worker service must not execute desktop surface"
    assert result["worker_response"]["dry_run"] is True, "worker response lost dry-run marker"
    assert result["request"]["payload"]["view"] == "full", "desktop payload changed"


def test_desktop_surface_worker_service_smoke() -> None:
    _run_smoke()


def main() -> int:
    try:
        _run_smoke()
    except AssertionError as exc:
        print("desktop_surface_worker_service_smoke failed")
        if str(exc):
            print(f"- {exc}")
        return 1
    print("desktop_surface_worker_service_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
