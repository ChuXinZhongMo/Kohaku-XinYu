from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from xinyu_bridge_codex_execution_backend import CODEX_EXECUTION_IN_PROCESS_BACKEND
from xinyu_bridge_codex_execution_contract import (
    CODEX_EXECUTION_DEFAULT_TIMEOUT_SECONDS,
    CODEX_EXECUTION_FALLBACK_ADAPTER,
    CODEX_EXECUTION_SERVICE_ID,
    CodexExecutionPlan,
)


CODEX_EXECUTION_WORKER_CLIENT_MODE = "worker_client_dry_run"
CODEX_EXECUTION_HTTP_WORKER_CLIENT_MODE = "worker_client_http"
CODEX_EXECUTION_WORKER_CLIENT_DEFAULT_ENABLED = False
CODEX_EXECUTION_WORKER_CLIENT_ROLLBACK = "unset_codex_execution_backend_and_use_in_process_backend"
CODEX_EXECUTION_WORKER_REQUEST_FIELDS = (
    "job_id",
    "payload",
    "text",
    "auto_study",
    "background",
    "timeout_seconds",
)
CODEX_EXECUTION_WORKER_RESPONSE_FIELDS = (
    "accepted",
    "service_id",
    "mode",
    "enabled",
    "ready",
    "dry_run",
    "fallback",
    "job_id",
    "status",
    "request",
)
CODEX_EXECUTION_WORKER_ENABLEMENT_GATES = (
    "worker_health_ready_smoke",
    "worker_submit_accepts_job_request_smoke",
    "worker_cancel_is_cooperative_and_idempotent_smoke",
    "worker_completion_outbox_records_success_failure_timeout_cancel_smoke",
    "worker_unhealthy_falls_back_to_in_process_backend_smoke",
    "rollback_unsets_runtime_backend_attr_smoke",
    "facade_route_payload_contract_unchanged_smoke",
)
CODEX_EXECUTION_WORKER_SATISFIED_ENABLEMENT_GATES = (
    "worker_health_ready_smoke",
    "worker_submit_accepts_job_request_smoke",
    "worker_cancel_is_cooperative_and_idempotent_smoke",
    "worker_completion_outbox_records_success_failure_timeout_cancel_smoke",
    "worker_unhealthy_falls_back_to_in_process_backend_smoke",
    "rollback_unsets_runtime_backend_attr_smoke",
    "facade_route_payload_contract_unchanged_smoke",
)


@dataclass(frozen=True, slots=True)
class CodexExecutionWorkerRequest:
    job_id: str
    payload: dict[str, Any]
    text: str
    auto_study: bool
    background: bool
    timeout_seconds: int


@dataclass(frozen=True, slots=True)
class CodexExecutionWorkerCompletionRecord:
    job_id: str
    status: str
    result: dict[str, Any]
    error: str
    completed_at: str


@dataclass(frozen=True, slots=True)
class CodexExecutionWorkerClientReadiness:
    service_id: str
    mode: str
    enabled: bool
    ready: bool
    fallback: str
    rollback: str
    request_fields: tuple[str, ...]
    response_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CodexExecutionWorkerEnablementChecklist:
    service_id: str
    mode: str
    ready: bool
    required_gates: tuple[str, ...]
    satisfied_gates: tuple[str, ...]
    missing_gates: tuple[str, ...]
    notes: tuple[str, ...] = ()


class DryRunCodexExecutionWorkerClient:
    mode = CODEX_EXECUTION_WORKER_CLIENT_MODE

    def __init__(
        self,
        *,
        enabled: bool = CODEX_EXECUTION_WORKER_CLIENT_DEFAULT_ENABLED,
        healthy: bool = True,
        endpoint: str = "",
        health_timeout_seconds: int = 5,
        submit_timeout_seconds: int = 30,
        cancel_timeout_seconds: int = 10,
    ) -> None:
        del endpoint, health_timeout_seconds, submit_timeout_seconds, cancel_timeout_seconds
        self.enabled = enabled
        self.healthy = healthy
        self._jobs: dict[str, CodexExecutionWorkerRequest] = {}
        self._completion_outbox: list[CodexExecutionWorkerCompletionRecord] = []

    def readiness(self) -> CodexExecutionWorkerClientReadiness:
        return CodexExecutionWorkerClientReadiness(
            service_id=CODEX_EXECUTION_SERVICE_ID,
            mode=self.mode,
            enabled=self.enabled,
            ready=self.enabled and self.healthy,
            fallback=CODEX_EXECUTION_FALLBACK_ADAPTER,
            rollback=CODEX_EXECUTION_WORKER_CLIENT_ROLLBACK,
            request_fields=CODEX_EXECUTION_WORKER_REQUEST_FIELDS,
            response_fields=CODEX_EXECUTION_WORKER_RESPONSE_FIELDS,
        )

    async def execute(self, runtime: Any, plan: CodexExecutionPlan) -> dict[str, Any]:
        del runtime
        request = codex_execution_worker_request_from_plan(plan)
        ready = self.readiness().ready
        if ready:
            self.submit(request)
        return {
            "accepted": ready,
            "service_id": CODEX_EXECUTION_SERVICE_ID,
            "mode": self.mode,
            "enabled": self.enabled,
            "ready": ready,
            "dry_run": True,
            "fallback": CODEX_EXECUTION_IN_PROCESS_BACKEND,
            "job_id": request.job_id,
            "status": "queued" if ready else "fallback_required",
            "request": {
                "job_id": request.job_id,
                "payload": request.payload,
                "text": request.text,
                "auto_study": request.auto_study,
                "background": request.background,
                "timeout_seconds": request.timeout_seconds,
            },
        }

    def submit(self, request: CodexExecutionWorkerRequest) -> dict[str, Any]:
        self._jobs[request.job_id] = request
        return {
            "accepted": True,
            "service_id": CODEX_EXECUTION_SERVICE_ID,
            "mode": self.mode,
            "job_id": request.job_id,
            "status": "queued",
            "request": {
                "job_id": request.job_id,
                "payload": dict(request.payload),
                "text": request.text,
                "auto_study": request.auto_study,
                "background": request.background,
                "timeout_seconds": request.timeout_seconds,
            },
        }

    def cancel(self, job_id: str, *, reason: str = "") -> dict[str, Any]:
        existing = next(
            (record for record in self._completion_outbox if record.job_id == job_id and record.status == "cancel_requested"),
            None,
        )
        if existing is None:
            existing = self.record_completion(
                job_id,
                status="cancel_requested",
                error=reason,
            )
        return {
            "accepted": True,
            "service_id": CODEX_EXECUTION_SERVICE_ID,
            "job_id": job_id,
            "status": existing.status,
            "cancel_requested": True,
            "cancel_reason": existing.error,
        }

    def record_completion(
        self,
        job_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: str = "",
    ) -> CodexExecutionWorkerCompletionRecord:
        record = CodexExecutionWorkerCompletionRecord(
            job_id=job_id,
            status=status,
            result=dict(result or {}),
            error=str(error or ""),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        self._completion_outbox.append(record)
        return record

    def completion_outbox(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "job_id": record.job_id,
                "status": record.status,
                "result": dict(record.result),
                "error": record.error,
                "completed_at": record.completed_at,
            }
            for record in self._completion_outbox
        )


WorkerTransport = Callable[[str, str, dict[str, Any], int], dict[str, Any]]


class HttpCodexExecutionWorkerClient:
    mode = CODEX_EXECUTION_HTTP_WORKER_CLIENT_MODE

    def __init__(
        self,
        *,
        endpoint: str,
        enabled: bool = CODEX_EXECUTION_WORKER_CLIENT_DEFAULT_ENABLED,
        healthy: bool = True,
        health_timeout_seconds: int = 5,
        submit_timeout_seconds: int = 30,
        cancel_timeout_seconds: int = 10,
        transport: WorkerTransport | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.enabled = enabled
        self.healthy = healthy
        self.health_timeout_seconds = health_timeout_seconds
        self.submit_timeout_seconds = submit_timeout_seconds
        self.cancel_timeout_seconds = cancel_timeout_seconds
        self._transport = _default_json_transport if transport is None else transport

    def readiness(self) -> CodexExecutionWorkerClientReadiness:
        return CodexExecutionWorkerClientReadiness(
            service_id=CODEX_EXECUTION_SERVICE_ID,
            mode=self.mode,
            enabled=self.enabled,
            ready=self.enabled and self.healthy and bool(self.endpoint),
            fallback=CODEX_EXECUTION_FALLBACK_ADAPTER,
            rollback=CODEX_EXECUTION_WORKER_CLIENT_ROLLBACK,
            request_fields=CODEX_EXECUTION_WORKER_REQUEST_FIELDS,
            response_fields=CODEX_EXECUTION_WORKER_RESPONSE_FIELDS,
        )

    async def execute(self, runtime: Any, plan: CodexExecutionPlan) -> dict[str, Any]:
        del runtime
        request = codex_execution_worker_request_from_plan(plan)
        if not self.readiness().ready:
            return _worker_fallback_response(self.mode, self.enabled, request)
        return self.submit(request)

    def submit(self, request: CodexExecutionWorkerRequest) -> dict[str, Any]:
        response = self._transport(
            "POST",
            f"{self.endpoint}/codex/execute",
            _worker_request_payload(request),
            self.submit_timeout_seconds,
        )
        return _normalize_worker_response(self.mode, self.enabled, request, response)

    def cancel(self, job_id: str, *, reason: str = "") -> dict[str, Any]:
        response = self._transport(
            "POST",
            f"{self.endpoint}/codex/cancel",
            {"job_id": job_id, "reason": reason},
            self.cancel_timeout_seconds,
        )
        return {
            "accepted": bool(response.get("accepted", True)),
            "service_id": CODEX_EXECUTION_SERVICE_ID,
            "job_id": str(response.get("job_id") or job_id),
            "status": str(response.get("status") or "cancel_requested"),
            "cancel_requested": bool(response.get("cancel_requested", True)),
            "cancel_reason": str(response.get("cancel_reason") or reason),
        }


def build_codex_execution_worker_client(
    *,
    endpoint: str = "",
    enabled: bool = CODEX_EXECUTION_WORKER_CLIENT_DEFAULT_ENABLED,
    healthy: bool = True,
    health_timeout_seconds: int = 5,
    submit_timeout_seconds: int = 30,
    cancel_timeout_seconds: int = 10,
    transport: WorkerTransport | None = None,
) -> DryRunCodexExecutionWorkerClient | HttpCodexExecutionWorkerClient:
    if endpoint.strip():
        return HttpCodexExecutionWorkerClient(
            endpoint=endpoint,
            enabled=enabled,
            healthy=healthy,
            health_timeout_seconds=health_timeout_seconds,
            submit_timeout_seconds=submit_timeout_seconds,
            cancel_timeout_seconds=cancel_timeout_seconds,
            transport=transport,
        )
    return DryRunCodexExecutionWorkerClient(
        enabled=enabled,
        healthy=healthy,
        health_timeout_seconds=health_timeout_seconds,
        submit_timeout_seconds=submit_timeout_seconds,
        cancel_timeout_seconds=cancel_timeout_seconds,
    )


def codex_execution_worker_request_from_plan(plan: CodexExecutionPlan) -> CodexExecutionWorkerRequest:
    payload = dict(plan.payload)
    job_id = str(payload.get("job_id") or "").strip()
    if not job_id:
        job_id = "codex-worker-dry-run"
    timeout_seconds = payload.get("timeout_seconds", CODEX_EXECUTION_DEFAULT_TIMEOUT_SECONDS)
    try:
        normalized_timeout = int(timeout_seconds)
    except (TypeError, ValueError):
        normalized_timeout = CODEX_EXECUTION_DEFAULT_TIMEOUT_SECONDS
    return CodexExecutionWorkerRequest(
        job_id=job_id,
        payload=payload,
        text=plan.text,
        auto_study=plan.auto_study,
        background=plan.background,
        timeout_seconds=normalized_timeout,
    )


def codex_execution_worker_client_readiness(
    *,
    enabled: bool = CODEX_EXECUTION_WORKER_CLIENT_DEFAULT_ENABLED,
) -> CodexExecutionWorkerClientReadiness:
    return DryRunCodexExecutionWorkerClient(enabled=enabled).readiness()


def _worker_request_payload(request: CodexExecutionWorkerRequest) -> dict[str, Any]:
    return {
        "job_id": request.job_id,
        "payload": dict(request.payload),
        "text": request.text,
        "auto_study": request.auto_study,
        "background": request.background,
        "timeout_seconds": request.timeout_seconds,
    }


def _worker_fallback_response(
    mode: str,
    enabled: bool,
    request: CodexExecutionWorkerRequest,
) -> dict[str, Any]:
    return {
        "accepted": False,
        "service_id": CODEX_EXECUTION_SERVICE_ID,
        "mode": mode,
        "enabled": enabled,
        "ready": False,
        "dry_run": mode == CODEX_EXECUTION_WORKER_CLIENT_MODE,
        "fallback": CODEX_EXECUTION_IN_PROCESS_BACKEND,
        "job_id": request.job_id,
        "status": "fallback_required",
        "request": _worker_request_payload(request),
    }


def _normalize_worker_response(
    mode: str,
    enabled: bool,
    request: CodexExecutionWorkerRequest,
    response: dict[str, Any],
) -> dict[str, Any]:
    accepted = bool(response.get("accepted", True))
    return {
        "accepted": accepted,
        "service_id": CODEX_EXECUTION_SERVICE_ID,
        "mode": mode,
        "enabled": enabled,
        "ready": accepted,
        "dry_run": False,
        "fallback": CODEX_EXECUTION_IN_PROCESS_BACKEND,
        "job_id": str(response.get("job_id") or request.job_id),
        "status": str(response.get("status") or ("queued" if accepted else "fallback_required")),
        "request": _worker_request_payload(request),
    }


def _default_json_transport(method: str, url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except URLError as exc:
        return {"accepted": False, "status": "transport_error", "error": str(exc)}
    if not body.strip():
        return {"accepted": True, "status": "queued"}
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {"accepted": False, "status": "invalid_worker_response"}
    return parsed if isinstance(parsed, dict) else {"accepted": False, "status": "invalid_worker_response"}


def codex_execution_worker_enablement_checklist(
    satisfied_gates: tuple[str, ...] | None = None,
) -> CodexExecutionWorkerEnablementChecklist:
    provided = CODEX_EXECUTION_WORKER_SATISFIED_ENABLEMENT_GATES if satisfied_gates is None else satisfied_gates
    provided_gates = set(provided)
    normalized_satisfied = tuple(
        gate for gate in CODEX_EXECUTION_WORKER_ENABLEMENT_GATES if gate in provided_gates
    )
    missing = tuple(
        gate for gate in CODEX_EXECUTION_WORKER_ENABLEMENT_GATES if gate not in normalized_satisfied
    )
    notes = (
        (
            "worker_enablement_gates_satisfied",
            "ready_means_boundary_contract_not_external_process_started",
        )
        if not missing
        else (
            "dry_run_worker_client_does_not_satisfy_enablement_by_itself",
            "do_not_set_process_split_ready_until_all_enablement_gates_pass",
        )
    )
    return CodexExecutionWorkerEnablementChecklist(
        service_id=CODEX_EXECUTION_SERVICE_ID,
        mode=CODEX_EXECUTION_WORKER_CLIENT_MODE,
        ready=not missing,
        required_gates=CODEX_EXECUTION_WORKER_ENABLEMENT_GATES,
        satisfied_gates=normalized_satisfied,
        missing_gates=missing,
        notes=notes,
    )
