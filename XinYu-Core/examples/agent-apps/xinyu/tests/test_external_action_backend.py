from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from xinyu_bridge_external_action_backend import (
    EXTERNAL_ACTION_BACKEND_DISABLED_MODE,
    EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE,
    EXTERNAL_ACTION_BACKEND_HTTP_MODE,
    EXTERNAL_ACTION_BACKEND_ROLLBACK,
    EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR,
    EXTERNAL_ACTION_S3_PREFLIGHT_GATES,
    EXTERNAL_ACTION_S3_SATISFIED_GATES,
    ApprovedExternalActionRequest,
    DryRunExternalActionExecutionBackend,
    HttpExternalActionExecutionBackend,
    build_external_action_execution_backend,
    external_action_backend_for_runtime,
    external_action_backend_readiness,
    external_action_s3_preflight_contract,
)
from xinyu_bridge_external_action_contract import (
    EXTERNAL_ACTION_APPROVAL_OWNER,
    EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS,
    EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES,
    EXTERNAL_ACTION_FALLBACK_ADAPTER,
    EXTERNAL_ACTION_ROLLBACK,
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


def test_external_action_backend_default_disabled() -> None:
    runtime = SimpleNamespace()
    backend = external_action_backend_for_runtime(runtime)
    readiness = external_action_backend_readiness(runtime)

    assert backend.mode == EXTERNAL_ACTION_BACKEND_DISABLED_MODE
    assert readiness.service_id == "external_action"
    assert readiness.mode == EXTERNAL_ACTION_BACKEND_DISABLED_MODE
    assert readiness.ready is False
    assert readiness.runtime_attr == EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR
    assert readiness.fallback_adapter == EXTERNAL_ACTION_FALLBACK_ADAPTER
    assert readiness.rollback == EXTERNAL_ACTION_BACKEND_ROLLBACK
    assert readiness.contract_rollback == EXTERNAL_ACTION_ROLLBACK
    assert "disabled_by_default_contract_only" in readiness.notes
    assert "does_not_mutate_public_readiness_or_worklog" in readiness.notes


def test_external_action_s3_preflight_ready_while_backend_stays_disabled() -> None:
    contract = external_action_s3_preflight_contract()

    assert contract.service_id == "external_action"
    assert contract.ready is True
    assert contract.required_gates == EXTERNAL_ACTION_S3_PREFLIGHT_GATES
    assert contract.satisfied_gates == EXTERNAL_ACTION_S3_SATISFIED_GATES
    assert contract.missing_gates == ()
    assert "backend_remains_disabled_by_default" in contract.notes
    assert external_action_backend_for_runtime(SimpleNamespace()).mode == EXTERNAL_ACTION_BACKEND_DISABLED_MODE


def test_external_action_s3_preflight_tracks_missing_gates() -> None:
    contract = external_action_s3_preflight_contract(
        (
            "backend_selection_contract",
            "approved_request_shape_contract",
            "not_a_gate",
        )
    )

    assert contract.ready is False
    assert contract.satisfied_gates == (
        "backend_selection_contract",
        "approved_request_shape_contract",
    )
    assert "not_a_gate" not in contract.satisfied_gates
    assert "dry_run_execution_backend_contract" in contract.missing_gates
    assert "in_process_fallback_rollback_contract" in contract.missing_gates


def test_external_action_dry_run_request_shape_records_approved_input_contract() -> None:
    runtime = SimpleNamespace(external_plugin_call=lambda payload: {"executed": payload})
    response = asyncio.run(external_action_backend_for_runtime(runtime).execute(runtime, _approved_request()))

    assert response["status"] == "backend_disabled"
    assert response["dry_run"] is True
    assert response["executed"] is False
    assert response["request"] == {
        "route": "/external/call",
        "http_method": "POST",
        "runtime_method": "external_plugin_call",
        "payload": {"plugin": "status", "args": {"target": "self"}},
        "query": {"trace": "dry-run"},
        "approved_by": EXTERNAL_ACTION_APPROVAL_OWNER,
        "approval_id": "policy-approval-1",
        "bridge_token_context": "verified_by_api_policy",
        "owner_private_context": False,
    }
    assert response["approved_request_inputs"] == EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS
    assert response["denied_policy_responsibilities"] == EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES
    assert "approve_or_reject_external_action_requests" in response["denied_policy_responsibilities"]
    assert "mutate_public_readiness_or_worklog" in response["denied_policy_responsibilities"]


def test_external_action_backend_does_not_execute_runtime_method_when_disabled() -> None:
    calls: list[str] = []

    def external_plugin_call(payload):
        calls.append("external_plugin_call")
        raise AssertionError("runtime method must not be executed by dry-run backend")

    runtime = SimpleNamespace(external_plugin_call=external_plugin_call)
    response = asyncio.run(external_action_backend_for_runtime(runtime).execute(runtime, _approved_request()))

    assert response["runtime_facade_present"] is True
    assert response["fallback_runtime_method"] == "external_plugin_call"
    assert response["fallback_runtime_facades"] == "current_in_process_runtime_facades"
    assert "runtime_method_not_invoked" in response["notes"]
    assert calls == []


def test_external_action_backend_enabled_still_only_returns_dry_run_response() -> None:
    calls: list[str] = []

    def external_plugin_call(payload):
        calls.append("external_plugin_call")
        raise AssertionError("enabled contract backend is still dry-run only")

    runtime = SimpleNamespace(external_plugin_call=external_plugin_call)
    backend = DryRunExternalActionExecutionBackend(enabled=True)

    response = asyncio.run(backend.execute(runtime, _approved_request()))

    assert backend.mode == EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE
    assert response["status"] == "dry_run_ready"
    assert response["enabled"] is True
    assert response["dry_run"] is True
    assert response["executed"] is False
    assert response["request"]["runtime_method"] == "external_plugin_call"
    assert response["fallback_runtime_method"] == "external_plugin_call"
    assert calls == []


def test_external_action_backend_factory_selects_http_backend_when_endpoint_is_configured() -> None:
    backend = build_external_action_execution_backend(
        mode=EXTERNAL_ACTION_BACKEND_HTTP_MODE,
        enabled=True,
        endpoint="http://127.0.0.1:8787",
    )

    assert isinstance(backend, HttpExternalActionExecutionBackend)
    assert backend.mode == EXTERNAL_ACTION_BACKEND_HTTP_MODE
    assert backend.enabled is True


def test_external_action_http_backend_executes_only_approved_request_shape() -> None:
    calls: list[tuple[str, str, dict[str, Any], int]] = []

    def transport(method: str, url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
        calls.append((method, url, payload, timeout_seconds))
        return {"accepted": True, "executed": True, "status": "accepted"}

    backend = HttpExternalActionExecutionBackend(
        endpoint="http://127.0.0.1:8787/",
        enabled=True,
        timeout_seconds=8,
        transport=transport,
    )
    runtime = SimpleNamespace(external_plugin_call=lambda payload: {"executed": payload})

    response = asyncio.run(backend.execute(runtime, _approved_request()))

    assert response["service_id"] == "external_action"
    assert response["mode"] == EXTERNAL_ACTION_BACKEND_HTTP_MODE
    assert response["enabled"] is True
    assert response["dry_run"] is False
    assert response["executed"] is True
    assert response["runtime_facade_present"] is True
    assert response["request"]["runtime_method"] == "external_plugin_call"
    assert response["approved_request_inputs"] == EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS
    assert response["denied_policy_responsibilities"] == EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES
    assert calls == [
        (
            "POST",
            "http://127.0.0.1:8787/external-action/execute",
            _approved_request().dry_run_shape(),
            8,
        )
    ]
