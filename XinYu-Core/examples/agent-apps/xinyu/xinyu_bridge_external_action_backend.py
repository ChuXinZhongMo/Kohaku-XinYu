from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from xinyu_bridge_external_action_contract import (
    EXTERNAL_ACTION_APPROVAL_OWNER,
    EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS,
    EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES,
    EXTERNAL_ACTION_FALLBACK_ADAPTER,
    EXTERNAL_ACTION_ROLLBACK,
    EXTERNAL_ACTION_STATE_OWNER,
)


EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR = "_external_action_execution_backend"
EXTERNAL_ACTION_SERVICE_ID = "external_action"
EXTERNAL_ACTION_BACKEND_DISABLED_MODE = "disabled_contract_only_dry_run_backend"
EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE = "external_action_execution_backend_dry_run"
EXTERNAL_ACTION_BACKEND_HTTP_MODE = "external_action_execution_backend_http"
EXTERNAL_ACTION_BACKEND_ROLLBACK = "remove_runtime_backend_attr_to_use_current_in_process_facades"
EXTERNAL_ACTION_S3_PREFLIGHT_GATES = (
    "backend_selection_contract",
    "dry_run_execution_backend_contract",
    "approved_request_shape_contract",
    "approval_execution_boundary_contract",
    "denied_policy_responsibilities_contract",
    "in_process_fallback_rollback_contract",
)
EXTERNAL_ACTION_S3_SATISFIED_GATES = EXTERNAL_ACTION_S3_PREFLIGHT_GATES


@dataclass(frozen=True, slots=True)
class ApprovedExternalActionRequest:
    route: str
    http_method: str
    runtime_method: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    query: Mapping[str, Any] = field(default_factory=dict)
    approved_by: str = EXTERNAL_ACTION_APPROVAL_OWNER
    approval_id: str = ""
    bridge_token_context: str = "verified_by_api_policy"
    owner_private_context: bool = False

    def dry_run_shape(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "http_method": self.http_method,
            "runtime_method": self.runtime_method,
            "payload": dict(self.payload),
            "query": dict(self.query),
            "approved_by": self.approved_by,
            "approval_id": self.approval_id,
            "bridge_token_context": self.bridge_token_context,
            "owner_private_context": self.owner_private_context,
        }


class ExternalActionExecutionBackend(Protocol):
    mode: str

    async def execute(self, runtime: Any, request: ApprovedExternalActionRequest) -> dict[str, Any]:
        ...


@dataclass(frozen=True, slots=True)
class ExternalActionBackendReadiness:
    service_id: str
    mode: str
    ready: bool
    runtime_attr: str
    state_owner: str
    fallback_adapter: str
    rollback: str
    contract_rollback: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExternalActionS3PreflightContract:
    service_id: str
    ready: bool
    required_gates: tuple[str, ...]
    satisfied_gates: tuple[str, ...]
    missing_gates: tuple[str, ...]
    rollback: str
    notes: tuple[str, ...] = ()


class DryRunExternalActionExecutionBackend:
    def __init__(self, *, enabled: bool = False, endpoint: str = "", mode: str = "") -> None:
        del endpoint, mode
        self.enabled = bool(enabled)
        self.mode = EXTERNAL_ACTION_BACKEND_DRY_RUN_MODE if self.enabled else EXTERNAL_ACTION_BACKEND_DISABLED_MODE

    async def execute(self, runtime: Any, request: ApprovedExternalActionRequest) -> dict[str, Any]:
        runtime_facade_present = hasattr(runtime, request.runtime_method)
        status = "dry_run_ready" if self.enabled else "backend_disabled"
        return {
            "service_id": EXTERNAL_ACTION_SERVICE_ID,
            "status": status,
            "mode": self.mode,
            "enabled": self.enabled,
            "dry_run": True,
            "executed": False,
            "request": request.dry_run_shape(),
            "runtime_facade_present": runtime_facade_present,
            "fallback_adapter": EXTERNAL_ACTION_FALLBACK_ADAPTER,
            "fallback_runtime_method": request.runtime_method,
            "fallback_runtime_facades": "current_in_process_runtime_facades",
            "rollback": EXTERNAL_ACTION_BACKEND_ROLLBACK,
            "contract_rollback": EXTERNAL_ACTION_ROLLBACK,
            "approved_request_inputs": EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS,
            "denied_policy_responsibilities": EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES,
            "notes": (
                "contract_only_no_external_action_executed",
                "runtime_method_not_invoked",
                "policy_approval_remains_owned_by_api_route_boundary",
                "future_enabled_backend_must_fall_back_to_current_in_process_runtime_facades",
            ),
        }


ExternalActionTransport = Callable[[str, str, dict[str, Any], int], dict[str, Any]]


class HttpExternalActionExecutionBackend:
    mode = EXTERNAL_ACTION_BACKEND_HTTP_MODE

    def __init__(
        self,
        *,
        endpoint: str,
        enabled: bool = False,
        timeout_seconds: int = 30,
        transport: ExternalActionTransport | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.enabled = bool(enabled)
        self.timeout_seconds = timeout_seconds
        self._transport = _default_json_transport if transport is None else transport

    async def execute(self, runtime: Any, request: ApprovedExternalActionRequest) -> dict[str, Any]:
        runtime_facade_present = hasattr(runtime, request.runtime_method)
        if not self.enabled or not self.endpoint:
            return _external_action_backend_response(
                mode=self.mode,
                enabled=self.enabled,
                executed=False,
                status="backend_disabled",
                dry_run=False,
                request=request,
                runtime_facade_present=runtime_facade_present,
            )
        response = self._transport(
            "POST",
            f"{self.endpoint}/external-action/execute",
            request.dry_run_shape(),
            self.timeout_seconds,
        )
        return _external_action_backend_response(
            mode=self.mode,
            enabled=self.enabled,
            executed=bool(response.get("executed", response.get("accepted", False))),
            status=str(response.get("status") or "accepted"),
            dry_run=False,
            request=request,
            runtime_facade_present=runtime_facade_present,
            response=dict(response),
        )


def build_external_action_execution_backend(
    *,
    mode: str = EXTERNAL_ACTION_BACKEND_DISABLED_MODE,
    enabled: bool = False,
    endpoint: str = "",
    timeout_seconds: int = 30,
    transport: ExternalActionTransport | None = None,
) -> DryRunExternalActionExecutionBackend | HttpExternalActionExecutionBackend:
    if mode == EXTERNAL_ACTION_BACKEND_HTTP_MODE or endpoint.strip():
        return HttpExternalActionExecutionBackend(
            endpoint=endpoint,
            enabled=enabled,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )
    return DryRunExternalActionExecutionBackend(enabled=enabled)


DISABLED_EXTERNAL_ACTION_BACKEND = DryRunExternalActionExecutionBackend(enabled=False)


def external_action_backend_for_runtime(
    runtime: Any,
    *,
    explicit_backend: ExternalActionExecutionBackend | None = None,
) -> ExternalActionExecutionBackend:
    if explicit_backend is not None:
        return explicit_backend
    runtime_backend = getattr(runtime, EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR, None)
    if runtime_backend is not None:
        return runtime_backend
    return DISABLED_EXTERNAL_ACTION_BACKEND


def external_action_backend_readiness(
    runtime: Any,
    *,
    explicit_backend: ExternalActionExecutionBackend | None = None,
) -> ExternalActionBackendReadiness:
    backend = external_action_backend_for_runtime(runtime, explicit_backend=explicit_backend)
    return ExternalActionBackendReadiness(
        service_id=EXTERNAL_ACTION_SERVICE_ID,
        mode=getattr(backend, "mode", type(backend).__name__),
        ready=False,
        runtime_attr=EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR,
        state_owner=EXTERNAL_ACTION_STATE_OWNER,
        fallback_adapter=EXTERNAL_ACTION_FALLBACK_ADAPTER,
        rollback=EXTERNAL_ACTION_BACKEND_ROLLBACK,
        contract_rollback=EXTERNAL_ACTION_ROLLBACK,
        notes=(
            "disabled_by_default_contract_only",
            "dry_run_only_until_execution_worker_is_connected",
            "fallback_to_current_in_process_runtime_facades",
            "does_not_mutate_public_readiness_or_worklog",
        ),
    )


def external_action_s3_preflight_contract(
    satisfied_gates: tuple[str, ...] | None = None,
) -> ExternalActionS3PreflightContract:
    provided_gates = set(EXTERNAL_ACTION_S3_SATISFIED_GATES if satisfied_gates is None else satisfied_gates)
    normalized_satisfied = tuple(gate for gate in EXTERNAL_ACTION_S3_PREFLIGHT_GATES if gate in provided_gates)
    missing = tuple(gate for gate in EXTERNAL_ACTION_S3_PREFLIGHT_GATES if gate not in normalized_satisfied)
    return ExternalActionS3PreflightContract(
        service_id=EXTERNAL_ACTION_SERVICE_ID,
        ready=not missing,
        required_gates=EXTERNAL_ACTION_S3_PREFLIGHT_GATES,
        satisfied_gates=normalized_satisfied,
        missing_gates=missing,
        rollback=EXTERNAL_ACTION_BACKEND_ROLLBACK,
        notes=(
            "s3_preflight_contract_only",
            "backend_remains_disabled_by_default",
            "execution_backend_must_perform_only_already_approved_work",
        ),
    )


def _external_action_backend_response(
    *,
    mode: str,
    enabled: bool,
    executed: bool,
    status: str,
    dry_run: bool,
    request: ApprovedExternalActionRequest,
    runtime_facade_present: bool,
    response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "service_id": EXTERNAL_ACTION_SERVICE_ID,
        "status": status,
        "mode": mode,
        "enabled": enabled,
        "dry_run": dry_run,
        "executed": executed,
        "request": request.dry_run_shape(),
        "runtime_facade_present": runtime_facade_present,
        "fallback_adapter": EXTERNAL_ACTION_FALLBACK_ADAPTER,
        "fallback_runtime_method": request.runtime_method,
        "fallback_runtime_facades": "current_in_process_runtime_facades",
        "rollback": EXTERNAL_ACTION_BACKEND_ROLLBACK,
        "contract_rollback": EXTERNAL_ACTION_ROLLBACK,
        "approved_request_inputs": EXTERNAL_ACTION_EXECUTION_ADAPTER_ALLOWED_INPUTS,
        "denied_policy_responsibilities": EXTERNAL_ACTION_EXECUTION_ADAPTER_DENIED_RESPONSIBILITIES,
        "worker_response": dict(response or {}),
        "notes": (
            "approved_request_only",
            "policy_approval_remains_owned_by_api_route_boundary",
            "future_enabled_backend_must_fall_back_to_current_in_process_runtime_facades",
        ),
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
        return {"accepted": True, "status": "accepted"}
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {"accepted": False, "status": "invalid_worker_response"}
    return parsed if isinstance(parsed, dict) else {"accepted": False, "status": "invalid_worker_response"}
