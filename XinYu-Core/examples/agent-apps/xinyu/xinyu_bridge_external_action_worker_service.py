from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping
from urllib.parse import urlparse

from xinyu_bridge_external_action_backend import (
    EXTERNAL_ACTION_BACKEND_ROLLBACK,
    EXTERNAL_ACTION_SERVICE_ID,
    ApprovedExternalActionRequest,
    ExternalActionTransport,
)
from xinyu_bridge_external_action_contract import (
    EXTERNAL_ACTION_APPROVAL_OWNER,
    EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS,
    EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES,
    EXTERNAL_ACTION_FALLBACK_ADAPTER,
    EXTERNAL_ACTION_ROLLBACK,
)


EXTERNAL_ACTION_WORKER_SERVICE_MODE = "external_action_worker_service_dry_run"
EXTERNAL_ACTION_WORKER_SERVICE_ROUTES = (
    "/health",
    "/external-action/execute",
    "/external-action/executions",
)
EXTERNAL_ACTION_WORKER_SERVICE_ROLLBACK = "stop_external_action_worker_and_unset_execution_backend"


@dataclass(frozen=True, slots=True)
class ExternalActionWorkerServiceReadiness:
    service_id: str
    mode: str
    ready: bool
    dry_run: bool
    executes_runtime: bool
    approval_owner: str
    routes: tuple[str, ...]
    allowed_inputs: tuple[str, ...]
    denied_responsibilities: tuple[str, ...]
    fallback_adapter: str
    rollback: str
    contract_rollback: str
    notes: tuple[str, ...] = ()


class ExternalActionWorkerService:
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = bool(ready)
        self._executions: list[dict[str, Any]] = []

    def readiness(self) -> ExternalActionWorkerServiceReadiness:
        return ExternalActionWorkerServiceReadiness(
            service_id=EXTERNAL_ACTION_SERVICE_ID,
            mode=EXTERNAL_ACTION_WORKER_SERVICE_MODE,
            ready=self.ready,
            dry_run=True,
            executes_runtime=False,
            approval_owner=EXTERNAL_ACTION_APPROVAL_OWNER,
            routes=EXTERNAL_ACTION_WORKER_SERVICE_ROUTES,
            allowed_inputs=EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS,
            denied_responsibilities=EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES,
            fallback_adapter=EXTERNAL_ACTION_FALLBACK_ADAPTER,
            rollback=EXTERNAL_ACTION_WORKER_SERVICE_ROLLBACK,
            contract_rollback=EXTERNAL_ACTION_ROLLBACK,
            notes=("dry_run_worker_service", "performs_only_already_approved_work", "does_not_execute_runtime"),
        )

    def handle_request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        normalized_method = str(method or "").upper()
        normalized_path = _normalize_path(path)
        request_payload = dict(payload or {})

        if normalized_method == "GET" and normalized_path == "/health":
            readiness = self.readiness()
            return {"ok": readiness.ready, **asdict(readiness)}
        if normalized_method == "POST" and normalized_path == "/external-action/execute":
            return self._execute(request_payload)
        if normalized_method == "GET" and normalized_path == "/external-action/executions":
            return {
                "service_id": EXTERNAL_ACTION_SERVICE_ID,
                "mode": EXTERNAL_ACTION_WORKER_SERVICE_MODE,
                "items": list(self._executions),
            }
        if normalized_path in EXTERNAL_ACTION_WORKER_SERVICE_ROUTES:
            return _error_response("method_not_allowed", http_status=405)
        return _error_response("not_found", http_status=404)

    def _execute(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = approved_external_action_request_from_payload(payload)
        request_shape = request.dry_run_shape()
        if not self.ready:
            return {
                "accepted": False,
                "executed": False,
                "service_id": EXTERNAL_ACTION_SERVICE_ID,
                "status": "fallback_required",
                "mode": EXTERNAL_ACTION_WORKER_SERVICE_MODE,
                "dry_run": True,
                "request": request_shape,
                "fallback_adapter": EXTERNAL_ACTION_FALLBACK_ADAPTER,
                "rollback": EXTERNAL_ACTION_BACKEND_ROLLBACK,
                "contract_rollback": EXTERNAL_ACTION_ROLLBACK,
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
            "service_id": EXTERNAL_ACTION_SERVICE_ID,
            "status": "dry_run_accepted",
            "mode": EXTERNAL_ACTION_WORKER_SERVICE_MODE,
            "dry_run": True,
            "request": request_shape,
            "fallback_adapter": EXTERNAL_ACTION_FALLBACK_ADAPTER,
            "rollback": EXTERNAL_ACTION_BACKEND_ROLLBACK,
            "contract_rollback": EXTERNAL_ACTION_ROLLBACK,
            "approved_request_inputs": EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS,
            "denied_policy_responsibilities": EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES,
            "notes": (
                "runtime_method_not_invoked",
                "policy_approval_remains_route_owned",
                "worker_service_dry_run_only",
            ),
        }


def approved_external_action_request_from_payload(payload: Mapping[str, Any]) -> ApprovedExternalActionRequest:
    nested_payload = payload.get("payload")
    query = payload.get("query")
    return ApprovedExternalActionRequest(
        route=str(payload.get("route") or ""),
        http_method=str(payload.get("http_method") or "POST"),
        runtime_method=str(payload.get("runtime_method") or ""),
        payload=dict(nested_payload) if isinstance(nested_payload, Mapping) else {},
        query=dict(query) if isinstance(query, Mapping) else {},
        approved_by=str(payload.get("approved_by") or EXTERNAL_ACTION_APPROVAL_OWNER),
        approval_id=str(payload.get("approval_id") or ""),
        bridge_token_context=str(payload.get("bridge_token_context") or "verified_by_api_policy"),
        owner_private_context=bool(payload.get("owner_private_context", False)),
    )


def external_action_worker_service_transport(service: ExternalActionWorkerService) -> ExternalActionTransport:
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
        "service_id": EXTERNAL_ACTION_SERVICE_ID,
        "status": status,
        "http_status": http_status,
    }


__all__ = [
    "EXTERNAL_ACTION_WORKER_SERVICE_MODE",
    "EXTERNAL_ACTION_WORKER_SERVICE_ROUTES",
    "EXTERNAL_ACTION_WORKER_SERVICE_ROLLBACK",
    "ExternalActionWorkerService",
    "ExternalActionWorkerServiceReadiness",
    "approved_external_action_request_from_payload",
    "external_action_worker_service_transport",
]
