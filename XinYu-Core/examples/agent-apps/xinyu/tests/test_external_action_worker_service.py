from __future__ import annotations

import asyncio
from types import SimpleNamespace

from xinyu_bridge_external_action_backend import (
    EXTERNAL_ACTION_BACKEND_HTTP_MODE,
    ApprovedExternalActionRequest,
    HttpExternalActionExecutionBackend,
)
from xinyu_bridge_external_action_contract import (
    EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS,
    EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES,
)
from xinyu_bridge_external_action_worker_service import (
    EXTERNAL_ACTION_WORKER_SERVICE_MODE,
    EXTERNAL_ACTION_WORKER_SERVICE_ROUTES,
    ExternalActionWorkerService,
    approved_external_action_request_from_payload,
    external_action_worker_service_transport,
)


def _approved_request() -> ApprovedExternalActionRequest:
    return ApprovedExternalActionRequest(
        route="/external/call",
        http_method="POST",
        runtime_method="external_plugin_call",
        payload={"plugin": "status", "args": {"target": "self"}},
        query={"trace": "dry-run"},
        approval_id="policy-approval-1",
    )


def test_external_action_worker_service_readiness_is_dry_run_and_policy_safe() -> None:
    readiness = ExternalActionWorkerService().readiness()

    assert readiness.service_id == "external_action"
    assert readiness.mode == EXTERNAL_ACTION_WORKER_SERVICE_MODE
    assert readiness.ready is True
    assert readiness.dry_run is True
    assert readiness.executes_runtime is False
    assert readiness.routes == EXTERNAL_ACTION_WORKER_SERVICE_ROUTES
    assert readiness.allowed_inputs == EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS
    assert readiness.denied_responsibilities == EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES
    assert "does_not_execute_runtime" in readiness.notes


def test_external_action_worker_service_health_route_exposes_readiness_payload() -> None:
    health = ExternalActionWorkerService().handle_request("GET", "/health")

    assert health["ok"] is True
    assert health["service_id"] == "external_action"
    assert health["mode"] == EXTERNAL_ACTION_WORKER_SERVICE_MODE
    assert tuple(health["routes"]) == EXTERNAL_ACTION_WORKER_SERVICE_ROUTES
    assert health["executes_runtime"] is False


def test_external_action_worker_service_execute_records_dry_run_only() -> None:
    service = ExternalActionWorkerService()

    result = service.handle_request("POST", "/external-action/execute", _approved_request().dry_run_shape())
    executions = service.handle_request("GET", "/external-action/executions")

    assert result["accepted"] is True
    assert result["executed"] is False
    assert result["dry_run"] is True
    assert result["mode"] == EXTERNAL_ACTION_WORKER_SERVICE_MODE
    assert result["request"] == _approved_request().dry_run_shape()
    assert "runtime_method_not_invoked" in result["notes"]
    assert executions["items"] == [
        {
            "status": "dry_run_accepted",
            "executed": False,
            "request": _approved_request().dry_run_shape(),
        }
    ]


def test_external_action_worker_service_transport_connects_http_backend_without_execution() -> None:
    service = ExternalActionWorkerService()
    backend = HttpExternalActionExecutionBackend(
        endpoint="http://127.0.0.1:8788/",
        enabled=True,
        transport=external_action_worker_service_transport(service),
    )
    runtime = SimpleNamespace(external_plugin_call=lambda payload: {"executed": payload})

    response = asyncio.run(backend.execute(runtime, _approved_request()))

    assert response["service_id"] == "external_action"
    assert response["mode"] == EXTERNAL_ACTION_BACKEND_HTTP_MODE
    assert response["enabled"] is True
    assert response["dry_run"] is False
    assert response["executed"] is False
    assert response["status"] == "dry_run_accepted"
    assert response["worker_response"]["dry_run"] is True
    assert response["worker_response"]["executed"] is False


def test_external_action_worker_service_not_ready_requests_fallback() -> None:
    result = ExternalActionWorkerService(ready=False).handle_request(
        "POST",
        "/external-action/execute",
        _approved_request().dry_run_shape(),
    )

    assert result["accepted"] is False
    assert result["executed"] is False
    assert result["status"] == "fallback_required"
    assert result["fallback_adapter"] == "in_process_runtime_route_methods"


def test_external_action_worker_service_rejects_unknown_or_invalid_routes() -> None:
    service = ExternalActionWorkerService()

    assert service.handle_request("GET", "/missing")["http_status"] == 404
    assert service.handle_request("GET", "/external-action/execute")["http_status"] == 405


def test_approved_external_action_request_from_payload_uses_policy_safe_defaults() -> None:
    request = approved_external_action_request_from_payload({"payload": {"value": 1}})

    assert request.route == ""
    assert request.http_method == "POST"
    assert request.runtime_method == ""
    assert request.payload == {"value": 1}
    assert request.query == {}
    assert request.approved_by == "api_policy_http_route_boundary"
    assert request.bridge_token_context == "verified_by_api_policy"
    assert request.owner_private_context is False
