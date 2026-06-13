from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping
from urllib.parse import urlparse

from xinyu_bridge_proactive_delivery_contract import (
    PROACTIVE_DELIVERY_FALLBACK_ADAPTER,
    PROACTIVE_DELIVERY_ROLLBACK,
)
from xinyu_bridge_proactive_delivery_route_backend import (
    PROACTIVE_DELIVERY_ROUTE_BACKEND_ROLLBACK,
    PROACTIVE_DELIVERY_SERVICE_ID,
    ProactiveDeliveryRouteRequest,
    ProactiveDeliveryTransport,
)


PROACTIVE_DELIVERY_WORKER_SERVICE_MODE = "proactive_delivery_route_backend_service_dry_run"
PROACTIVE_DELIVERY_WORKER_SERVICE_ROUTES = (
    "/health",
    "/proactive-delivery/execute",
    "/proactive-delivery/executions",
)
PROACTIVE_DELIVERY_WORKER_SERVICE_ROLLBACK = "stop_proactive_delivery_worker_and_unset_route_backend"


@dataclass(frozen=True, slots=True)
class ProactiveDeliveryWorkerServiceReadiness:
    service_id: str
    mode: str
    ready: bool
    dry_run: bool
    mutates_state: bool
    touches_qq_gateway: bool
    routes: tuple[str, ...]
    fallback_adapter: str
    rollback: str
    contract_rollback: str
    notes: tuple[str, ...] = ()


class ProactiveDeliveryWorkerService:
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = bool(ready)
        self._executions: list[dict[str, Any]] = []

    def readiness(self) -> ProactiveDeliveryWorkerServiceReadiness:
        return ProactiveDeliveryWorkerServiceReadiness(
            service_id=PROACTIVE_DELIVERY_SERVICE_ID,
            mode=PROACTIVE_DELIVERY_WORKER_SERVICE_MODE,
            ready=self.ready,
            dry_run=True,
            mutates_state=False,
            touches_qq_gateway=False,
            routes=PROACTIVE_DELIVERY_WORKER_SERVICE_ROUTES,
            fallback_adapter=PROACTIVE_DELIVERY_FALLBACK_ADAPTER,
            rollback=PROACTIVE_DELIVERY_WORKER_SERVICE_ROLLBACK,
            contract_rollback=PROACTIVE_DELIVERY_ROLLBACK,
            notes=("dry_run_route_backend_service", "does_not_touch_qq_gateway", "does_not_mutate_outbox_state"),
        )

    def handle_request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        normalized_method = str(method or "").upper()
        normalized_path = _normalize_path(path)
        request_payload = dict(payload or {})

        if normalized_method == "GET" and normalized_path == "/health":
            readiness = self.readiness()
            return {"ok": readiness.ready, **asdict(readiness)}
        if normalized_method == "POST" and normalized_path == "/proactive-delivery/execute":
            return self._execute(request_payload)
        if normalized_method == "GET" and normalized_path == "/proactive-delivery/executions":
            return {
                "service_id": PROACTIVE_DELIVERY_SERVICE_ID,
                "mode": PROACTIVE_DELIVERY_WORKER_SERVICE_MODE,
                "items": list(self._executions),
            }
        if normalized_path in PROACTIVE_DELIVERY_WORKER_SERVICE_ROUTES:
            return _error_response("method_not_allowed", http_status=405)
        return _error_response("not_found", http_status=404)

    def _execute(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = proactive_delivery_route_request_from_payload(payload)
        request_shape = request.dry_run_shape()
        if not self.ready:
            return {
                "accepted": False,
                "executed": False,
                "service_id": PROACTIVE_DELIVERY_SERVICE_ID,
                "status": "fallback_required",
                "mode": PROACTIVE_DELIVERY_WORKER_SERVICE_MODE,
                "dry_run": True,
                "request": request_shape,
                "fallback_adapter": PROACTIVE_DELIVERY_FALLBACK_ADAPTER,
                "rollback": PROACTIVE_DELIVERY_ROUTE_BACKEND_ROLLBACK,
                "contract_rollback": PROACTIVE_DELIVERY_ROLLBACK,
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
            "service_id": PROACTIVE_DELIVERY_SERVICE_ID,
            "status": "dry_run_accepted",
            "mode": PROACTIVE_DELIVERY_WORKER_SERVICE_MODE,
            "dry_run": True,
            "request": request_shape,
            "fallback_adapter": PROACTIVE_DELIVERY_FALLBACK_ADAPTER,
            "rollback": PROACTIVE_DELIVERY_ROUTE_BACKEND_ROLLBACK,
            "contract_rollback": PROACTIVE_DELIVERY_ROLLBACK,
            "notes": (
                "runtime_method_not_invoked",
                "qq_gateway_not_touched",
                "outbox_state_not_mutated",
                "claim_ack_idempotency_remains_in_fallback",
            ),
        }


def proactive_delivery_route_request_from_payload(payload: Mapping[str, Any]) -> ProactiveDeliveryRouteRequest:
    nested_payload = payload.get("payload")
    query = payload.get("query")
    return ProactiveDeliveryRouteRequest(
        route=str(payload.get("route") or ""),
        http_method=str(payload.get("http_method") or "POST"),
        runtime_method=str(payload.get("runtime_method") or ""),
        payload=dict(nested_payload) if isinstance(nested_payload, Mapping) else {},
        query=dict(query) if isinstance(query, Mapping) else {},
        fast_path=bool(payload.get("fast_path", False)),
    )


def proactive_delivery_worker_service_transport(service: ProactiveDeliveryWorkerService) -> ProactiveDeliveryTransport:
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
        "service_id": PROACTIVE_DELIVERY_SERVICE_ID,
        "status": status,
        "http_status": http_status,
    }


__all__ = [
    "PROACTIVE_DELIVERY_WORKER_SERVICE_MODE",
    "PROACTIVE_DELIVERY_WORKER_SERVICE_ROUTES",
    "PROACTIVE_DELIVERY_WORKER_SERVICE_ROLLBACK",
    "ProactiveDeliveryWorkerService",
    "ProactiveDeliveryWorkerServiceReadiness",
    "proactive_delivery_route_request_from_payload",
    "proactive_delivery_worker_service_transport",
]
