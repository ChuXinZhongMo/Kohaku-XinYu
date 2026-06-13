from __future__ import annotations

import asyncio
from types import SimpleNamespace

from xinyu_bridge_codex_execution_contract import CodexExecutionPlan
from xinyu_bridge_codex_execution_worker_client import (
    CODEX_EXECUTION_HTTP_WORKER_CLIENT_MODE,
    CODEX_EXECUTION_WORKER_REQUEST_FIELDS,
    CODEX_EXECUTION_WORKER_RESPONSE_FIELDS,
    HttpCodexExecutionWorkerClient,
)
from xinyu_bridge_codex_execution_worker_service import (
    CODEX_EXECUTION_WORKER_SERVICE_MODE,
    CODEX_EXECUTION_WORKER_SERVICE_ROUTES,
    CodexExecutionWorkerService,
    codex_execution_worker_request_from_payload,
    codex_execution_worker_service_transport,
)


def test_codex_worker_service_readiness_is_dry_run_and_process_safe() -> None:
    service = CodexExecutionWorkerService()
    readiness = service.readiness()

    assert readiness.service_id == "codex_execution"
    assert readiness.mode == CODEX_EXECUTION_WORKER_SERVICE_MODE
    assert readiness.ready is True
    assert readiness.dry_run is True
    assert readiness.executes_runtime is False
    assert readiness.routes == CODEX_EXECUTION_WORKER_SERVICE_ROUTES
    assert readiness.request_fields == CODEX_EXECUTION_WORKER_REQUEST_FIELDS
    assert readiness.response_fields == CODEX_EXECUTION_WORKER_RESPONSE_FIELDS
    assert "does_not_execute_codex_runtime" in readiness.notes


def test_codex_worker_service_health_route_exposes_readiness_payload() -> None:
    health = CodexExecutionWorkerService().handle_request("GET", "/health")

    assert health["ok"] is True
    assert health["service_id"] == "codex_execution"
    assert health["mode"] == CODEX_EXECUTION_WORKER_SERVICE_MODE
    assert tuple(health["routes"]) == CODEX_EXECUTION_WORKER_SERVICE_ROUTES
    assert health["executes_runtime"] is False


def test_codex_worker_service_submit_cancel_and_completion_outbox() -> None:
    service = CodexExecutionWorkerService()

    submit = service.handle_request(
        "POST",
        "/codex/execute",
        {
            "job_id": "codex-worker-service",
            "payload": {"job_id": "codex-worker-service", "task": "dry run"},
            "text": "run codex",
            "auto_study": False,
            "background": True,
            "timeout_seconds": 9,
        },
    )
    cancel = service.handle_request("POST", "/codex/cancel", {"job_id": "codex-worker-service", "reason": "owner"})
    outbox = service.handle_request("GET", "/codex/completions")

    assert submit["accepted"] is True
    assert submit["mode"] == CODEX_EXECUTION_WORKER_SERVICE_MODE
    assert submit["dry_run"] is True
    assert submit["request"] == {
        "job_id": "codex-worker-service",
        "payload": {"job_id": "codex-worker-service", "task": "dry run"},
        "text": "run codex",
        "auto_study": False,
        "background": True,
        "timeout_seconds": 9,
    }
    assert cancel["cancel_requested"] is True
    assert cancel["cancel_reason"] == "owner"
    assert outbox["items"][0]["job_id"] == "codex-worker-service"
    assert outbox["items"][0]["status"] == "cancel_requested"


def test_codex_worker_service_transport_connects_existing_http_client() -> None:
    service = CodexExecutionWorkerService()
    client = HttpCodexExecutionWorkerClient(
        endpoint="http://127.0.0.1:8787/",
        enabled=True,
        healthy=True,
        transport=codex_execution_worker_service_transport(service),
    )
    plan = CodexExecutionPlan(
        payload={"job_id": "codex-http-service", "timeout_seconds": 5},
        text="run codex",
        auto_study=False,
        background=False,
    )

    result = asyncio.run(client.execute(SimpleNamespace(), plan))

    assert result == {
        "accepted": True,
        "service_id": "codex_execution",
        "mode": CODEX_EXECUTION_HTTP_WORKER_CLIENT_MODE,
        "enabled": True,
        "ready": True,
        "dry_run": False,
        "fallback": "in_process_runtime_delegate_backend",
        "job_id": "codex-http-service",
        "status": "queued",
        "request": {
            "job_id": "codex-http-service",
            "payload": {"job_id": "codex-http-service", "timeout_seconds": 5},
            "text": "run codex",
            "auto_study": False,
            "background": False,
            "timeout_seconds": 5,
        },
    }


def test_codex_worker_service_not_ready_requests_fallback() -> None:
    response = CodexExecutionWorkerService(ready=False).handle_request(
        "POST",
        "/codex/execute",
        {"job_id": "codex-not-ready"},
    )

    assert response["accepted"] is False
    assert response["ready"] is False
    assert response["status"] == "fallback_required"
    assert response["fallback"] == "in_process_runtime_delegate_backend"


def test_codex_worker_service_rejects_unknown_or_invalid_routes() -> None:
    service = CodexExecutionWorkerService()

    assert service.handle_request("GET", "/missing")["http_status"] == 404
    assert service.handle_request("GET", "/codex/execute")["http_status"] == 405
    assert service.handle_request("POST", "/codex/cancel", {})["http_status"] == 400


def test_codex_worker_request_from_payload_uses_safe_defaults() -> None:
    request = codex_execution_worker_request_from_payload({"timeout_seconds": "bad"})

    assert request.job_id == "codex-worker-dry-run"
    assert request.payload == {"timeout_seconds": "bad"}
    assert request.text == ""
    assert request.auto_study is False
    assert request.background is False
    assert request.timeout_seconds == 1800
