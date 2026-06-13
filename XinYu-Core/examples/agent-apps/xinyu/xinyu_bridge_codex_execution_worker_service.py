from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from xinyu_bridge_codex_execution_backend import CODEX_EXECUTION_IN_PROCESS_BACKEND
from xinyu_bridge_codex_execution_contract import (
    CODEX_EXECUTION_DEFAULT_TIMEOUT_SECONDS,
    CODEX_EXECUTION_SERVICE_ID,
)
from xinyu_bridge_codex_execution_worker_client import (
    CODEX_EXECUTION_WORKER_CLIENT_MODE,
    CODEX_EXECUTION_WORKER_CLIENT_ROLLBACK,
    CODEX_EXECUTION_WORKER_REQUEST_FIELDS,
    CODEX_EXECUTION_WORKER_RESPONSE_FIELDS,
    CodexExecutionWorkerRequest,
    DryRunCodexExecutionWorkerClient,
    WorkerTransport,
)


CODEX_EXECUTION_WORKER_SERVICE_MODE = "codex_execution_worker_service_dry_run"
CODEX_EXECUTION_WORKER_SERVICE_ROUTES = (
    "/health",
    "/codex/execute",
    "/codex/cancel",
    "/codex/completions",
)
CODEX_EXECUTION_WORKER_SERVICE_ROLLBACK = "stop_worker_process_and_unset_codex_execution_backend"


@dataclass(frozen=True, slots=True)
class CodexExecutionWorkerServiceReadiness:
    service_id: str
    mode: str
    ready: bool
    dry_run: bool
    executes_runtime: bool
    routes: tuple[str, ...]
    request_fields: tuple[str, ...]
    response_fields: tuple[str, ...]
    fallback: str
    rollback: str
    notes: tuple[str, ...] = ()


class CodexExecutionWorkerService:
    def __init__(
        self,
        *,
        ready: bool = True,
        worker_client: DryRunCodexExecutionWorkerClient | None = None,
    ) -> None:
        self.ready = bool(ready)
        self.worker_client = worker_client or DryRunCodexExecutionWorkerClient(
            enabled=True,
            healthy=self.ready,
        )

    def readiness(self) -> CodexExecutionWorkerServiceReadiness:
        return CodexExecutionWorkerServiceReadiness(
            service_id=CODEX_EXECUTION_SERVICE_ID,
            mode=CODEX_EXECUTION_WORKER_SERVICE_MODE,
            ready=self.ready and self.worker_client.readiness().ready,
            dry_run=True,
            executes_runtime=False,
            routes=CODEX_EXECUTION_WORKER_SERVICE_ROUTES,
            request_fields=CODEX_EXECUTION_WORKER_REQUEST_FIELDS,
            response_fields=CODEX_EXECUTION_WORKER_RESPONSE_FIELDS,
            fallback=CODEX_EXECUTION_IN_PROCESS_BACKEND,
            rollback=CODEX_EXECUTION_WORKER_SERVICE_ROLLBACK,
            notes=("dry_run_worker_service", "does_not_execute_codex_runtime"),
        )

    def handle_request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        normalized_method = str(method or "").upper()
        normalized_path = _normalize_path(path)
        request_payload = dict(payload or {})

        if normalized_method == "GET" and normalized_path == "/health":
            readiness = self.readiness()
            return {"ok": readiness.ready, **asdict(readiness)}
        if normalized_method == "POST" and normalized_path == "/codex/execute":
            return self._submit(request_payload)
        if normalized_method == "POST" and normalized_path == "/codex/cancel":
            return self._cancel(request_payload)
        if normalized_method == "GET" and normalized_path == "/codex/completions":
            return {
                "service_id": CODEX_EXECUTION_SERVICE_ID,
                "mode": CODEX_EXECUTION_WORKER_SERVICE_MODE,
                "items": list(self.worker_client.completion_outbox()),
            }
        if normalized_path in CODEX_EXECUTION_WORKER_SERVICE_ROUTES:
            return _error_response("method_not_allowed", http_status=405)
        return _error_response("not_found", http_status=404)

    def _submit(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = codex_execution_worker_request_from_payload(payload)
        readiness = self.readiness()
        if not readiness.ready:
            return {
                "accepted": False,
                "service_id": CODEX_EXECUTION_SERVICE_ID,
                "mode": CODEX_EXECUTION_WORKER_SERVICE_MODE,
                "enabled": True,
                "ready": False,
                "dry_run": True,
                "fallback": CODEX_EXECUTION_IN_PROCESS_BACKEND,
                "job_id": request.job_id,
                "status": "fallback_required",
                "request": _worker_request_payload(request),
                "rollback": CODEX_EXECUTION_WORKER_CLIENT_ROLLBACK,
            }
        response = self.worker_client.submit(request)
        response.update(
            {
                "mode": CODEX_EXECUTION_WORKER_SERVICE_MODE,
                "enabled": True,
                "ready": True,
                "dry_run": True,
                "fallback": CODEX_EXECUTION_IN_PROCESS_BACKEND,
                "worker_client_mode": CODEX_EXECUTION_WORKER_CLIENT_MODE,
            }
        )
        return response

    def _cancel(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        job_id = str(payload.get("job_id") or "").strip()
        if not job_id:
            return _error_response("missing_job_id", http_status=400)
        return self.worker_client.cancel(job_id, reason=str(payload.get("reason") or ""))


def codex_execution_worker_request_from_payload(payload: Mapping[str, Any]) -> CodexExecutionWorkerRequest:
    nested_payload = payload.get("payload")
    request_payload = dict(nested_payload) if isinstance(nested_payload, Mapping) else dict(payload)
    job_id = str(payload.get("job_id") or request_payload.get("job_id") or "codex-worker-dry-run").strip()
    return CodexExecutionWorkerRequest(
        job_id=job_id,
        payload=request_payload,
        text=str(payload.get("text") or request_payload.get("text") or ""),
        auto_study=bool(payload.get("auto_study", False)),
        background=bool(payload.get("background", False)),
        timeout_seconds=_safe_timeout(payload.get("timeout_seconds")),
    )


def codex_execution_worker_service_transport(
    service: CodexExecutionWorkerService,
) -> WorkerTransport:
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


def _worker_request_payload(request: CodexExecutionWorkerRequest) -> dict[str, Any]:
    return {
        "job_id": request.job_id,
        "payload": dict(request.payload),
        "text": request.text,
        "auto_study": request.auto_study,
        "background": request.background,
        "timeout_seconds": request.timeout_seconds,
    }


def _safe_timeout(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = CODEX_EXECUTION_DEFAULT_TIMEOUT_SECONDS
    return max(1, parsed)


def _error_response(status: str, *, http_status: int) -> dict[str, Any]:
    return {
        "accepted": False,
        "service_id": CODEX_EXECUTION_SERVICE_ID,
        "status": status,
        "http_status": http_status,
    }


__all__ = [
    "CODEX_EXECUTION_WORKER_SERVICE_MODE",
    "CODEX_EXECUTION_WORKER_SERVICE_ROUTES",
    "CODEX_EXECUTION_WORKER_SERVICE_ROLLBACK",
    "CodexExecutionWorkerService",
    "CodexExecutionWorkerServiceReadiness",
    "codex_execution_worker_request_from_payload",
    "codex_execution_worker_service_transport",
]
