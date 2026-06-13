from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[3]
ROOT_TEXT = str(ROOT)
if ROOT_TEXT not in sys.path:
    sys.path.insert(0, ROOT_TEXT)

from xinyu_bridge_proactive_delivery_route_backend import HttpProactiveDeliveryRouteBackend, ProactiveDeliveryRouteRequest
from xinyu_bridge_proactive_delivery_worker_service import (
    PROACTIVE_DELIVERY_WORKER_SERVICE_MODE,
    ProactiveDeliveryWorkerService,
    proactive_delivery_worker_service_transport,
)


def _run_smoke() -> None:
    service = ProactiveDeliveryWorkerService()
    health = service.handle_request("GET", "/health")
    assert health["ok"] is True, "proactive delivery worker service health is not ready"
    assert health["mode"] == PROACTIVE_DELIVERY_WORKER_SERVICE_MODE, "worker service mode changed"
    assert health["touches_qq_gateway"] is False, "worker service must not touch QQ gateway"

    backend = HttpProactiveDeliveryRouteBackend(
        endpoint="http://127.0.0.1:8789",
        enabled=True,
        transport=proactive_delivery_worker_service_transport(service),
    )
    request = ProactiveDeliveryRouteRequest(
        route="/qq/outbox/claim",
        http_method="POST",
        runtime_method="qq_outbox_claim",
        payload={"claim_id": "smoke-claim"},
    )
    result = backend.execute_sync(SimpleNamespace(qq_outbox_claim=lambda payload: payload), request)

    assert result["status"] == "dry_run_accepted", "worker service did not accept route request"
    assert result["executed"] is False, "dry-run worker service must not execute proactive delivery"
    assert result["worker_response"]["dry_run"] is True, "worker response lost dry-run marker"
    assert result["request"]["payload"]["claim_id"] == "smoke-claim", "claim payload changed"


def test_proactive_delivery_worker_service_smoke() -> None:
    _run_smoke()


def main() -> int:
    try:
        _run_smoke()
    except AssertionError as exc:
        print("proactive_delivery_worker_service_smoke failed")
        if str(exc):
            print(f"- {exc}")
        return 1
    print("proactive_delivery_worker_service_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
