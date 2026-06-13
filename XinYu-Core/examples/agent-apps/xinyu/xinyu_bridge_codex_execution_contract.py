from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from xinyu_bridge_errors import BridgeRequestError


CODEX_EXECUTION_STATE_OWNER = "codex_presence_state_and_delegate_artifacts"
CODEX_EXECUTION_FALLBACK_ADAPTER = "in_process_runtime_codex_execute"
CODEX_EXECUTION_ROLLBACK = "route_codex_execute_back_to_xinyu_bridge_codex_runtime_facade"
CODEX_EXECUTION_SERVICE_ID = "codex_execution"
CODEX_EXECUTION_MODE = "in_process"
CODEX_EXECUTION_JOB_ID_FIELD = "job_id"
CODEX_EXECUTION_JOB_STATUS_FIELD = "status"
CODEX_EXECUTION_JOB_PAYLOAD_FIELD = "payload"
CODEX_EXECUTION_JOB_CREATED_AT_FIELD = "created_at"
CODEX_EXECUTION_JOB_TIMEOUT_SECONDS_FIELD = "timeout_seconds"
CODEX_EXECUTION_CANCEL_REQUEST_FIELD = "cancel_requested"
CODEX_EXECUTION_CANCEL_REASON_FIELD = "cancel_reason"
CODEX_EXECUTION_COMPLETION_OUTBOX = "codex_execution_completion_outbox"
CODEX_EXECUTION_HEALTH_READY_WHEN_STARTED = "ready_when_in_process_harness_started"
CODEX_EXECUTION_DEFAULT_TIMEOUT_SECONDS = 1800
CODEX_EXECUTION_JOB_REQUIRED_FIELDS = (
    CODEX_EXECUTION_JOB_ID_FIELD,
    CODEX_EXECUTION_JOB_STATUS_FIELD,
    CODEX_EXECUTION_JOB_PAYLOAD_FIELD,
    CODEX_EXECUTION_JOB_CREATED_AT_FIELD,
    CODEX_EXECUTION_JOB_TIMEOUT_SECONDS_FIELD,
)
CODEX_EXECUTION_JOB_STATUS_VALUES = (
    "queued",
    "running",
    "cancel_requested",
    "timeout",
    "completed",
    "failed",
)
CODEX_EXECUTION_COMPLETION_OUTBOX_FIELDS = (
    "job_id",
    "status",
    "result",
    "error",
    "completed_at",
)
CODEX_EXECUTION_CANCEL_SEMANTICS = (
    "cancel_is_cooperative",
    "cancel_preserves_route_and_runtime_facade",
    "cancel_records_completion_outbox_entry",
)
CODEX_EXECUTION_TIMEOUT_SEMANTICS = (
    "timeout_marks_job_timeout",
    "timeout_records_completion_outbox_entry",
    "timeout_keeps_in_process_fallback_adapter",
)


@dataclass(frozen=True, slots=True)
class CodexExecutionPlan:
    payload: dict[str, Any]
    text: str
    auto_study: bool
    background: bool


@dataclass(frozen=True, slots=True)
class CodexExecutionReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    state_owner: str
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CodexExecutionJobContract:
    required_fields: tuple[str, ...]
    status_values: tuple[str, ...]
    timeout_seconds_field: str
    default_timeout_seconds: int
    cancel_request_field: str
    cancel_reason_field: str


@dataclass(frozen=True, slots=True)
class CodexExecutionCompletionOutboxContract:
    name: str
    required_fields: tuple[str, ...]
    records_cancel: bool
    records_timeout: bool
    records_success: bool
    in_process_fallback: str


@dataclass(frozen=True, slots=True)
class CodexExecutionHealthContract:
    readiness_semantic: str
    service_id: str
    mode: str
    state_owner: str
    fallback_adapter: str


@dataclass(frozen=True, slots=True)
class CodexExecutionPreflightContract:
    job: CodexExecutionJobContract
    completion_outbox: CodexExecutionCompletionOutboxContract
    health: CodexExecutionHealthContract
    cancel_semantics: tuple[str, ...]
    timeout_semantics: tuple[str, ...]


class CodexExecutionHarness:
    def __init__(self) -> None:
        self._started = False

    def start(self) -> CodexExecutionReadiness:
        self._started = True
        return self.readiness()

    def stop(self) -> CodexExecutionReadiness:
        self._started = False
        return self.readiness()

    def readiness(self) -> CodexExecutionReadiness:
        return CodexExecutionReadiness(
            service_id=CODEX_EXECUTION_SERVICE_ID,
            mode=CODEX_EXECUTION_MODE,
            started=self._started,
            ready=self._started,
            state_owner=CODEX_EXECUTION_STATE_OWNER,
            fallback_adapter=CODEX_EXECUTION_FALLBACK_ADAPTER,
            rollback=CODEX_EXECUTION_ROLLBACK,
            notes=("foreground_and_background_paths_share_runtime_facade",),
        )

    @staticmethod
    def fallback_adapter(runtime_execute_func: Callable[..., Any]) -> Callable[..., Any]:
        return runtime_execute_func


CODEX_EXECUTION_PREFLIGHT_CONTRACT = CodexExecutionPreflightContract(
    job=CodexExecutionJobContract(
        required_fields=CODEX_EXECUTION_JOB_REQUIRED_FIELDS,
        status_values=CODEX_EXECUTION_JOB_STATUS_VALUES,
        timeout_seconds_field=CODEX_EXECUTION_JOB_TIMEOUT_SECONDS_FIELD,
        default_timeout_seconds=CODEX_EXECUTION_DEFAULT_TIMEOUT_SECONDS,
        cancel_request_field=CODEX_EXECUTION_CANCEL_REQUEST_FIELD,
        cancel_reason_field=CODEX_EXECUTION_CANCEL_REASON_FIELD,
    ),
    completion_outbox=CodexExecutionCompletionOutboxContract(
        name=CODEX_EXECUTION_COMPLETION_OUTBOX,
        required_fields=CODEX_EXECUTION_COMPLETION_OUTBOX_FIELDS,
        records_cancel=True,
        records_timeout=True,
        records_success=True,
        in_process_fallback=CODEX_EXECUTION_FALLBACK_ADAPTER,
    ),
    health=CodexExecutionHealthContract(
        readiness_semantic=CODEX_EXECUTION_HEALTH_READY_WHEN_STARTED,
        service_id=CODEX_EXECUTION_SERVICE_ID,
        mode=CODEX_EXECUTION_MODE,
        state_owner=CODEX_EXECUTION_STATE_OWNER,
        fallback_adapter=CODEX_EXECUTION_FALLBACK_ADAPTER,
    ),
    cancel_semantics=CODEX_EXECUTION_CANCEL_SEMANTICS,
    timeout_semantics=CODEX_EXECUTION_TIMEOUT_SEMANTICS,
)


def codex_execution_preflight_contract() -> CodexExecutionPreflightContract:
    return CODEX_EXECUTION_PREFLIGHT_CONTRACT


def normalize_codex_execution_payload(
    payload: dict[str, Any] | None,
    *,
    runtime_closed: bool,
) -> dict[str, Any]:
    if runtime_closed:
        raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
    if payload is not None and not isinstance(payload, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    return dict(payload or {})


def ensure_codex_execution_text(
    text: str,
    *,
    looks_like_codex_request_func: Callable[[str], bool],
    ambiguous_request_message: str,
) -> None:
    if not looks_like_codex_request_func(text):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, ambiguous_request_message)


def build_codex_execution_plan(
    payload: dict[str, Any],
    *,
    text: str,
    should_auto_study: Callable[[str], bool],
    prepare_payload_func: Callable[..., dict[str, bool]],
) -> CodexExecutionPlan:
    request_flags = prepare_payload_func(
        payload,
        text=text,
        should_auto_study=should_auto_study,
    )
    return CodexExecutionPlan(
        payload=payload,
        text=text,
        auto_study=bool(request_flags["auto_study"]),
        background=bool(request_flags["background"]),
    )
