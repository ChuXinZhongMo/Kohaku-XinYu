from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from xinyu_bridge_proactive_delivery_route_backend import (
    PROACTIVE_DELIVERY_BACKEND_HTTP_MODE,
    HttpProactiveDeliveryRouteBackend,
    ProactiveDeliveryRouteRequest,
)
from xinyu_bridge_proactive_delivery_worker_service import (
    PROACTIVE_DELIVERY_WORKER_SERVICE_MODE,
    PROACTIVE_DELIVERY_WORKER_SERVICE_ROUTES,
    ProactiveDeliveryWorkerService,
    proactive_delivery_route_request_from_payload,
    proactive_delivery_worker_service_transport,
)


def _runtime(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        xinyu_dir=root,
        qq_outbox_claim=lambda payload: {"claimed": payload},
        qq_outbox_claim_fast=lambda payload: {"claimed": payload},
    )


def _request() -> ProactiveDeliveryRouteRequest:
    return ProactiveDeliveryRouteRequest(
        route="/qq/outbox/claim",
        http_method="POST",
        runtime_method="qq_outbox_claim",
        payload={"claim_id": "claim-1"},
        query={"trace": "dry-run"},
        fast_path=False,
    )


def test_proactive_delivery_worker_service_readiness_is_dry_run_and_qq_safe() -> None:
    readiness = ProactiveDeliveryWorkerService().readiness()

    assert readiness.service_id == "proactive_delivery"
    assert readiness.mode == PROACTIVE_DELIVERY_WORKER_SERVICE_MODE
    assert readiness.ready is True
    assert readiness.dry_run is True
    assert readiness.mutates_state is False
    assert readiness.touches_qq_gateway is False
    assert readiness.routes == PROACTIVE_DELIVERY_WORKER_SERVICE_ROUTES
    assert "does_not_touch_qq_gateway" in readiness.notes


def test_proactive_delivery_worker_service_health_route_exposes_readiness_payload() -> None:
    health = ProactiveDeliveryWorkerService().handle_request("GET", "/health")

    assert health["ok"] is True
    assert health["service_id"] == "proactive_delivery"
    assert health["mode"] == PROACTIVE_DELIVERY_WORKER_SERVICE_MODE
    assert tuple(health["routes"]) == PROACTIVE_DELIVERY_WORKER_SERVICE_ROUTES
    assert health["touches_qq_gateway"] is False


def test_proactive_delivery_worker_service_execute_records_dry_run_only() -> None:
    service = ProactiveDeliveryWorkerService()

    result = service.handle_request("POST", "/proactive-delivery/execute", _request().dry_run_shape())
    executions = service.handle_request("GET", "/proactive-delivery/executions")

    assert result["accepted"] is True
    assert result["executed"] is False
    assert result["dry_run"] is True
    assert result["mode"] == PROACTIVE_DELIVERY_WORKER_SERVICE_MODE
    assert result["request"] == _request().dry_run_shape()
    assert "qq_gateway_not_touched" in result["notes"]
    assert executions["items"] == [
        {
            "status": "dry_run_accepted",
            "executed": False,
            "request": _request().dry_run_shape(),
        }
    ]


def test_proactive_delivery_worker_service_transport_connects_http_backend(tmp_path: Path) -> None:
    service = ProactiveDeliveryWorkerService()
    backend = HttpProactiveDeliveryRouteBackend(
        endpoint="http://127.0.0.1:8789/",
        enabled=True,
        transport=proactive_delivery_worker_service_transport(service),
    )

    response = backend.execute_sync(_runtime(tmp_path), _request())

    assert response["service_id"] == "proactive_delivery"
    assert response["mode"] == PROACTIVE_DELIVERY_BACKEND_HTTP_MODE
    assert response["dry_run"] is False
    assert response["executed"] is False
    assert response["status"] == "dry_run_accepted"
    assert response["worker_response"]["dry_run"] is True
    assert response["worker_response"]["executed"] is False


def test_proactive_delivery_worker_service_not_ready_requests_fallback() -> None:
    result = ProactiveDeliveryWorkerService(ready=False).handle_request(
        "POST",
        "/proactive-delivery/execute",
        _request().dry_run_shape(),
    )

    assert result["accepted"] is False
    assert result["executed"] is False
    assert result["status"] == "fallback_required"
    assert result["fallback_adapter"] == "in_process_proactive_delivery_runtime_methods"


def test_proactive_delivery_worker_service_rejects_unknown_or_invalid_routes() -> None:
    service = ProactiveDeliveryWorkerService()

    assert service.handle_request("GET", "/missing")["http_status"] == 404
    assert service.handle_request("GET", "/proactive-delivery/execute")["http_status"] == 405


def test_proactive_delivery_route_request_from_payload_uses_safe_defaults() -> None:
    request = proactive_delivery_route_request_from_payload({"payload": {"claim_id": "claim-1"}})

    assert request.route == ""
    assert request.http_method == "POST"
    assert request.runtime_method == ""
    assert request.payload == {"claim_id": "claim-1"}
    assert request.query == {}
    assert request.fast_path is False
