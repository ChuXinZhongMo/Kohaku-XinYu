from __future__ import annotations

from http import HTTPStatus

import pytest

from xinyu_bridge_codex_execution_contract import (
    CODEX_EXECUTION_CANCEL_REASON_FIELD,
    CODEX_EXECUTION_CANCEL_REQUEST_FIELD,
    CODEX_EXECUTION_CANCEL_SEMANTICS,
    CODEX_EXECUTION_COMPLETION_OUTBOX,
    CODEX_EXECUTION_COMPLETION_OUTBOX_FIELDS,
    CODEX_EXECUTION_DEFAULT_TIMEOUT_SECONDS,
    CODEX_EXECUTION_FALLBACK_ADAPTER,
    CODEX_EXECUTION_HEALTH_READY_WHEN_STARTED,
    CODEX_EXECUTION_JOB_CREATED_AT_FIELD,
    CODEX_EXECUTION_JOB_ID_FIELD,
    CODEX_EXECUTION_JOB_PAYLOAD_FIELD,
    CODEX_EXECUTION_JOB_REQUIRED_FIELDS,
    CODEX_EXECUTION_JOB_STATUS_FIELD,
    CODEX_EXECUTION_JOB_STATUS_VALUES,
    CODEX_EXECUTION_JOB_TIMEOUT_SECONDS_FIELD,
    CODEX_EXECUTION_ROLLBACK,
    CODEX_EXECUTION_STATE_OWNER,
    CODEX_EXECUTION_TIMEOUT_SEMANTICS,
    CodexExecutionHarness,
    build_codex_execution_plan,
    codex_execution_preflight_contract,
    ensure_codex_execution_text,
    normalize_codex_execution_payload,
)
from xinyu_bridge_errors import BridgeRequestError


def test_codex_execution_contract_rejects_closed_runtime() -> None:
    with pytest.raises(BridgeRequestError) as caught:
        normalize_codex_execution_payload({}, runtime_closed=True)

    assert caught.value.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert caught.value.message == "bridge is shutting down"


def test_codex_execution_contract_rejects_non_object_payload() -> None:
    with pytest.raises(BridgeRequestError) as caught:
        normalize_codex_execution_payload([], runtime_closed=False)  # type: ignore[arg-type]

    assert caught.value.status == HTTPStatus.BAD_REQUEST
    assert caught.value.message == "request body must be a JSON object"


def test_codex_execution_contract_copies_payload() -> None:
    original = {"text": "run codex"}
    normalized = normalize_codex_execution_payload(original, runtime_closed=False)

    assert normalized == original
    assert normalized is not original


def test_codex_execution_contract_rejects_ambiguous_text() -> None:
    with pytest.raises(BridgeRequestError) as caught:
        ensure_codex_execution_text(
            "plain chat",
            looks_like_codex_request_func=lambda text: False,
            ambiguous_request_message="ambiguous",
        )

    assert caught.value.status == HTTPStatus.BAD_REQUEST
    assert caught.value.message == "ambiguous"


def test_codex_execution_contract_builds_plan_from_payload_flags() -> None:
    calls: list[tuple[str, object]] = []
    payload: dict[str, object] = {"text": "run codex"}

    def prepare(payload_arg: dict[str, object], **kwargs: object) -> dict[str, bool]:
        calls.append(("prepare", {"payload": dict(payload_arg), **kwargs}))
        payload_arg["visible_window"] = True
        return {"auto_study": True, "background": False}

    plan = build_codex_execution_plan(
        payload,
        text="run codex with context",
        should_auto_study=lambda text: True,
        prepare_payload_func=prepare,
    )

    assert plan.payload is payload
    assert plan.text == "run codex with context"
    assert plan.auto_study is True
    assert plan.background is False
    assert payload["visible_window"] is True
    assert len(calls) == 1
    label, details = calls[0]
    assert label == "prepare"
    assert details["payload"] == {"text": "run codex"}  # type: ignore[index]
    assert details["text"] == "run codex with context"  # type: ignore[index]
    assert callable(details["should_auto_study"])  # type: ignore[index]


def test_codex_execution_preflight_contract_defines_job_fields() -> None:
    contract = codex_execution_preflight_contract()

    assert contract.job.required_fields == CODEX_EXECUTION_JOB_REQUIRED_FIELDS
    assert contract.job.required_fields == (
        CODEX_EXECUTION_JOB_ID_FIELD,
        CODEX_EXECUTION_JOB_STATUS_FIELD,
        CODEX_EXECUTION_JOB_PAYLOAD_FIELD,
        CODEX_EXECUTION_JOB_CREATED_AT_FIELD,
        CODEX_EXECUTION_JOB_TIMEOUT_SECONDS_FIELD,
    )
    assert contract.job.status_values == CODEX_EXECUTION_JOB_STATUS_VALUES
    assert {"queued", "running", "completed", "failed"}.issubset(contract.job.status_values)
    assert contract.job.timeout_seconds_field == CODEX_EXECUTION_JOB_TIMEOUT_SECONDS_FIELD
    assert contract.job.default_timeout_seconds == CODEX_EXECUTION_DEFAULT_TIMEOUT_SECONDS


def test_codex_execution_preflight_contract_defines_cancel_and_timeout_semantics() -> None:
    contract = codex_execution_preflight_contract()

    assert contract.job.cancel_request_field == CODEX_EXECUTION_CANCEL_REQUEST_FIELD
    assert contract.job.cancel_reason_field == CODEX_EXECUTION_CANCEL_REASON_FIELD
    assert contract.cancel_semantics == CODEX_EXECUTION_CANCEL_SEMANTICS
    assert "cancel_requested" in contract.job.status_values
    assert "cancel_records_completion_outbox_entry" in contract.cancel_semantics
    assert contract.timeout_semantics == CODEX_EXECUTION_TIMEOUT_SEMANTICS
    assert "timeout" in contract.job.status_values
    assert "timeout_records_completion_outbox_entry" in contract.timeout_semantics
    assert "timeout_keeps_in_process_fallback_adapter" in contract.timeout_semantics


def test_codex_execution_preflight_contract_defines_health_and_completion_outbox() -> None:
    contract = codex_execution_preflight_contract()

    assert contract.completion_outbox.name == CODEX_EXECUTION_COMPLETION_OUTBOX
    assert contract.completion_outbox.required_fields == CODEX_EXECUTION_COMPLETION_OUTBOX_FIELDS
    assert contract.completion_outbox.records_cancel is True
    assert contract.completion_outbox.records_timeout is True
    assert contract.completion_outbox.records_success is True
    assert contract.completion_outbox.in_process_fallback == CODEX_EXECUTION_FALLBACK_ADAPTER
    assert contract.health.readiness_semantic == CODEX_EXECUTION_HEALTH_READY_WHEN_STARTED
    assert contract.health.service_id == "codex_execution"
    assert contract.health.mode == "in_process"
    assert contract.health.state_owner == CODEX_EXECUTION_STATE_OWNER
    assert contract.health.fallback_adapter == CODEX_EXECUTION_FALLBACK_ADAPTER


def test_codex_execution_harness_lifecycle_readiness_and_fallback() -> None:
    harness = CodexExecutionHarness()

    initial = harness.readiness()
    assert initial.service_id == "codex_execution"
    assert initial.mode == "in_process"
    assert initial.started is False
    assert initial.ready is False
    assert initial.state_owner == CODEX_EXECUTION_STATE_OWNER
    assert initial.fallback_adapter == CODEX_EXECUTION_FALLBACK_ADAPTER
    assert initial.rollback == CODEX_EXECUTION_ROLLBACK

    started = harness.start()
    assert started.started is True
    assert started.ready is True

    def execute(payload: dict[str, object]) -> dict[str, object]:
        return {"accepted": True, "payload": payload}

    assert harness.fallback_adapter(execute)({"text": "run codex"}) == {
        "accepted": True,
        "payload": {"text": "run codex"},
    }

    stopped = harness.stop()
    assert stopped.started is False
    assert stopped.ready is False
