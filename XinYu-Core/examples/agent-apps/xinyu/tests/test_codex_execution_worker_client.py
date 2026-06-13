from __future__ import annotations

import asyncio
from types import SimpleNamespace

from xinyu_bridge_codex_execution import runtime_codex_execute
from xinyu_bridge_codex_execution_backend import (
    CODEX_EXECUTION_BACKEND_RUNTIME_ATTR,
    CODEX_EXECUTION_IN_PROCESS_BACKEND,
    IN_PROCESS_CODEX_EXECUTION_BACKEND,
    codex_execution_backend_for_runtime,
)
from xinyu_bridge_codex_execution_contract import (
    CODEX_EXECUTION_DEFAULT_TIMEOUT_SECONDS,
    CodexExecutionPlan,
)
from xinyu_bridge_codex_execution_worker_client import (
    CODEX_EXECUTION_HTTP_WORKER_CLIENT_MODE,
    CODEX_EXECUTION_WORKER_CLIENT_DEFAULT_ENABLED,
    CODEX_EXECUTION_WORKER_CLIENT_MODE,
    CODEX_EXECUTION_WORKER_CLIENT_ROLLBACK,
    CODEX_EXECUTION_WORKER_ENABLEMENT_GATES,
    CODEX_EXECUTION_WORKER_REQUEST_FIELDS,
    CODEX_EXECUTION_WORKER_RESPONSE_FIELDS,
    CODEX_EXECUTION_WORKER_SATISFIED_ENABLEMENT_GATES,
    DryRunCodexExecutionWorkerClient,
    HttpCodexExecutionWorkerClient,
    build_codex_execution_worker_client,
    codex_execution_worker_client_readiness,
    codex_execution_worker_enablement_checklist,
    codex_execution_worker_request_from_plan,
)


def test_codex_worker_client_is_disabled_by_default_and_not_selected() -> None:
    runtime = SimpleNamespace()
    readiness = codex_execution_worker_client_readiness()

    assert CODEX_EXECUTION_WORKER_CLIENT_DEFAULT_ENABLED is False
    assert readiness.service_id == "codex_execution"
    assert readiness.mode == CODEX_EXECUTION_WORKER_CLIENT_MODE
    assert readiness.enabled is False
    assert readiness.ready is False
    assert readiness.rollback == CODEX_EXECUTION_WORKER_CLIENT_ROLLBACK
    assert readiness.request_fields == CODEX_EXECUTION_WORKER_REQUEST_FIELDS
    assert readiness.response_fields == CODEX_EXECUTION_WORKER_RESPONSE_FIELDS
    assert codex_execution_backend_for_runtime(runtime) is IN_PROCESS_CODEX_EXECUTION_BACKEND


def test_codex_worker_client_readiness_tracks_health() -> None:
    assert DryRunCodexExecutionWorkerClient(enabled=True, healthy=True).readiness().ready is True
    assert DryRunCodexExecutionWorkerClient(enabled=True, healthy=False).readiness().ready is False


def test_codex_worker_client_factory_selects_http_client_when_endpoint_is_configured() -> None:
    client = build_codex_execution_worker_client(
        endpoint="http://127.0.0.1:8787",
        enabled=True,
        healthy=True,
    )
    readiness = client.readiness()

    assert isinstance(client, HttpCodexExecutionWorkerClient)
    assert readiness.service_id == "codex_execution"
    assert readiness.mode == CODEX_EXECUTION_HTTP_WORKER_CLIENT_MODE
    assert readiness.enabled is True
    assert readiness.ready is True
    assert readiness.rollback == CODEX_EXECUTION_WORKER_CLIENT_ROLLBACK


def test_codex_worker_enablement_checklist_tracks_satisfied_gates_by_default() -> None:
    checklist = codex_execution_worker_enablement_checklist()

    assert checklist.service_id == "codex_execution"
    assert checklist.mode == CODEX_EXECUTION_WORKER_CLIENT_MODE
    assert checklist.ready is True
    assert checklist.required_gates == CODEX_EXECUTION_WORKER_ENABLEMENT_GATES
    assert checklist.satisfied_gates == CODEX_EXECUTION_WORKER_SATISFIED_ENABLEMENT_GATES
    assert checklist.missing_gates == ()
    assert "worker_enablement_gates_satisfied" in checklist.notes
    assert "ready_means_boundary_contract_not_external_process_started" in checklist.notes


def test_codex_worker_enablement_checklist_tracks_missing_gates_in_required_order() -> None:
    satisfied = (
        "rollback_unsets_runtime_backend_attr_smoke",
        "worker_health_ready_smoke",
        "not_a_real_gate",
    )

    checklist = codex_execution_worker_enablement_checklist(satisfied)

    assert checklist.ready is False
    assert checklist.satisfied_gates == (
        "worker_health_ready_smoke",
        "rollback_unsets_runtime_backend_attr_smoke",
    )
    assert "not_a_real_gate" not in checklist.satisfied_gates
    assert "worker_submit_accepts_job_request_smoke" in checklist.missing_gates


def test_codex_worker_enablement_checklist_requires_all_gates() -> None:
    checklist = codex_execution_worker_enablement_checklist(CODEX_EXECUTION_WORKER_ENABLEMENT_GATES)

    assert checklist.ready is True
    assert checklist.satisfied_gates == CODEX_EXECUTION_WORKER_ENABLEMENT_GATES
    assert checklist.missing_gates == ()


def test_codex_worker_request_from_plan_freezes_payload_shape() -> None:
    plan = CodexExecutionPlan(
        payload={"job_id": "codex-1", "timeout_seconds": "42", "task": "run codex"},
        text="run codex with context",
        auto_study=True,
        background=True,
    )

    request = codex_execution_worker_request_from_plan(plan)

    assert request.job_id == "codex-1"
    assert request.payload == {"job_id": "codex-1", "timeout_seconds": "42", "task": "run codex"}
    assert request.text == "run codex with context"
    assert request.auto_study is True
    assert request.background is True
    assert request.timeout_seconds == 42


def test_codex_worker_request_uses_safe_defaults() -> None:
    plan = CodexExecutionPlan(
        payload={"timeout_seconds": "not-an-int"},
        text="run codex",
        auto_study=False,
        background=False,
    )

    request = codex_execution_worker_request_from_plan(plan)

    assert request.job_id == "codex-worker-dry-run"
    assert request.timeout_seconds == CODEX_EXECUTION_DEFAULT_TIMEOUT_SECONDS


def test_codex_worker_client_execute_accepts_dry_run_job_when_ready() -> None:
    client = DryRunCodexExecutionWorkerClient(enabled=True)
    plan = CodexExecutionPlan(
        payload={"job_id": "codex-1", "timeout_seconds": 5},
        text="run codex",
        auto_study=False,
        background=False,
    )
    runtime = SimpleNamespace()

    result = asyncio.run(client.execute(runtime, plan))

    assert result == {
        "accepted": True,
        "service_id": "codex_execution",
        "mode": CODEX_EXECUTION_WORKER_CLIENT_MODE,
        "enabled": True,
        "ready": True,
        "dry_run": True,
        "fallback": CODEX_EXECUTION_IN_PROCESS_BACKEND,
        "job_id": "codex-1",
        "status": "queued",
        "request": {
            "job_id": "codex-1",
            "payload": {"job_id": "codex-1", "timeout_seconds": 5},
            "text": "run codex",
            "auto_study": False,
            "background": False,
            "timeout_seconds": 5,
        },
    }
    assert client.completion_outbox() == ()


def test_codex_http_worker_client_uses_transport_without_changing_response_shape() -> None:
    calls: list[tuple[str, str, dict[str, Any], int]] = []

    def transport(method: str, url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
        calls.append((method, url, payload, timeout_seconds))
        return {"accepted": True, "job_id": payload["job_id"], "status": "queued"}

    client = HttpCodexExecutionWorkerClient(
        endpoint="http://127.0.0.1:8787/",
        enabled=True,
        healthy=True,
        submit_timeout_seconds=9,
        transport=transport,
    )
    plan = CodexExecutionPlan(
        payload={"job_id": "codex-http", "timeout_seconds": 5},
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
        "fallback": CODEX_EXECUTION_IN_PROCESS_BACKEND,
        "job_id": "codex-http",
        "status": "queued",
        "request": {
            "job_id": "codex-http",
            "payload": {"job_id": "codex-http", "timeout_seconds": 5},
            "text": "run codex",
            "auto_study": False,
            "background": False,
            "timeout_seconds": 5,
        },
    }
    assert calls == [
        (
            "POST",
            "http://127.0.0.1:8787/codex/execute",
            {
                "job_id": "codex-http",
                "payload": {"job_id": "codex-http", "timeout_seconds": 5},
                "text": "run codex",
                "auto_study": False,
                "background": False,
                "timeout_seconds": 5,
            },
            9,
        )
    ]


def test_codex_http_worker_client_cancel_uses_transport() -> None:
    calls: list[tuple[str, str, dict[str, Any], int]] = []

    def transport(method: str, url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
        calls.append((method, url, payload, timeout_seconds))
        return {"accepted": True, "job_id": payload["job_id"], "status": "cancel_requested"}

    client = HttpCodexExecutionWorkerClient(
        endpoint="http://127.0.0.1:8787",
        enabled=True,
        healthy=True,
        cancel_timeout_seconds=4,
        transport=transport,
    )

    result = client.cancel("codex-http", reason="owner")

    assert result == {
        "accepted": True,
        "service_id": "codex_execution",
        "job_id": "codex-http",
        "status": "cancel_requested",
        "cancel_requested": True,
        "cancel_reason": "owner",
    }
    assert calls == [
        (
            "POST",
            "http://127.0.0.1:8787/codex/cancel",
            {"job_id": "codex-http", "reason": "owner"},
            4,
        )
    ]


def test_codex_worker_client_unhealthy_response_requests_fallback() -> None:
    client = DryRunCodexExecutionWorkerClient(enabled=True, healthy=False)
    plan = CodexExecutionPlan(
        payload={"job_id": "codex-unhealthy"},
        text="run codex",
        auto_study=False,
        background=False,
    )

    result = asyncio.run(client.execute(SimpleNamespace(), plan))

    assert result["accepted"] is False
    assert result["ready"] is False
    assert result["status"] == "fallback_required"
    assert result["fallback"] == CODEX_EXECUTION_IN_PROCESS_BACKEND


def test_codex_worker_client_cancel_is_idempotent_and_records_outbox() -> None:
    client = DryRunCodexExecutionWorkerClient(enabled=True)
    request = codex_execution_worker_request_from_plan(
        CodexExecutionPlan(
            payload={"job_id": "codex-cancel"},
            text="run codex",
            auto_study=False,
            background=True,
        )
    )

    submit = client.submit(request)
    first = client.cancel("codex-cancel", reason="owner")
    second = client.cancel("codex-cancel", reason="ignored")
    outbox = client.completion_outbox()

    assert submit["status"] == "queued"
    assert first == {
        "accepted": True,
        "service_id": "codex_execution",
        "job_id": "codex-cancel",
        "status": "cancel_requested",
        "cancel_requested": True,
        "cancel_reason": "owner",
    }
    assert second == first
    assert len(outbox) == 1
    assert outbox[0]["job_id"] == "codex-cancel"
    assert outbox[0]["status"] == "cancel_requested"
    assert outbox[0]["error"] == "owner"
    assert outbox[0]["completed_at"]


def test_codex_worker_client_completion_outbox_records_terminal_statuses() -> None:
    client = DryRunCodexExecutionWorkerClient(enabled=True)

    client.record_completion("ok", status="completed", result={"reply": "done"})
    client.record_completion("fail", status="failed", error="failed")
    client.record_completion("timeout", status="timeout", error="timeout")

    outbox = client.completion_outbox()
    assert [record["status"] for record in outbox] == ["completed", "failed", "timeout"]
    assert outbox[0]["result"] == {"reply": "done"}
    assert outbox[1]["error"] == "failed"
    assert outbox[2]["error"] == "timeout"


def test_runtime_codex_execute_can_use_explicit_dry_run_backend_without_default_enablement() -> None:
    client = DryRunCodexExecutionWorkerClient(enabled=True)
    payload = {"text": "run codex", "background": False, "timeout_seconds": 7}
    runtime = SimpleNamespace(
        _closed=False,
        _payload_text=lambda payload: "run codex",
        _augment_codex_payload_with_dialogue_context=lambda payload, text: f"{text} with context",
        **{CODEX_EXECUTION_BACKEND_RUNTIME_ATTR: client},
    )

    result = asyncio.run(
        runtime_codex_execute(
            runtime,
            payload,
            should_auto_study=lambda text: False,
            looks_like_codex_request_func=lambda text: True,
            prepare_payload_func=lambda payload, **kwargs: {"auto_study": False, "background": False},
        )
    )

    assert result["mode"] == CODEX_EXECUTION_WORKER_CLIENT_MODE
    assert result["dry_run"] is True
    assert result["request"]["text"] == "run codex with context"
    assert result["request"]["timeout_seconds"] == 7
