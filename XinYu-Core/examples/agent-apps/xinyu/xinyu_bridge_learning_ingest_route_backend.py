from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from xinyu_bridge_learning_ingest_contract import learning_ingest_contract


LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR = "_learning_ingest_route_backend"
LEARNING_INGEST_SERVICE_ID = "learning_ingest"
LEARNING_INGEST_BACKEND_DISABLED_MODE = "disabled_contract_only_learning_route_backend"
LEARNING_INGEST_BACKEND_DRY_RUN_MODE = "learning_ingest_route_backend_dry_run"
LEARNING_INGEST_ROUTE_BACKEND_ROLLBACK = "remove_runtime_learning_backend_attr_to_use_learning_service"


@dataclass(frozen=True, slots=True)
class LearningIngestRouteRequest:
    route: str
    http_method: str
    runtime_method: str
    service_method: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def dry_run_shape(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "http_method": self.http_method,
            "runtime_method": self.runtime_method,
            "service_method": self.service_method,
            "payload": dict(self.payload),
        }


class LearningIngestRouteBackend(Protocol):
    mode: str

    async def execute(self, runtime: Any, request: LearningIngestRouteRequest) -> dict[str, Any]:
        ...


@dataclass(frozen=True, slots=True)
class LearningIngestRouteBackendReadiness:
    service_id: str
    mode: str
    ready: bool
    local_only: bool
    fallback_adapter: str
    rollback: str
    runtime_attr: str
    contract_rollback: str
    notes: tuple[str, ...] = ()


class DryRunLearningIngestRouteBackend:
    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = bool(enabled)
        self.mode = LEARNING_INGEST_BACKEND_DRY_RUN_MODE if self.enabled else LEARNING_INGEST_BACKEND_DISABLED_MODE

    async def execute(self, runtime: Any, request: LearningIngestRouteRequest) -> dict[str, Any]:
        return {
            "service_id": LEARNING_INGEST_SERVICE_ID,
            "status": "dry_run_ready" if self.enabled else "backend_disabled",
            "mode": self.mode,
            "enabled": self.enabled,
            "dry_run": True,
            "executed": False,
            "request": request.dry_run_shape(),
            "fallback_adapter": "runtime.learning_service",
            "fallback_service_method": request.service_method,
            "rollback": LEARNING_INGEST_ROUTE_BACKEND_ROLLBACK,
            "notes": (
                "contract_only_no_learning_state_written",
                "learning_service_method_not_invoked",
                "reviewed_memory_gate_remains_local",
            ),
        }


DISABLED_LEARNING_INGEST_ROUTE_BACKEND = DryRunLearningIngestRouteBackend(enabled=False)


def learning_ingest_route_backend_for_runtime(
    runtime: Any,
    *,
    explicit_backend: LearningIngestRouteBackend | None = None,
) -> LearningIngestRouteBackend:
    if explicit_backend is not None:
        return explicit_backend
    runtime_backend = getattr(runtime, LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR, None)
    if runtime_backend is not None:
        return runtime_backend
    return DISABLED_LEARNING_INGEST_ROUTE_BACKEND


def learning_ingest_route_backend_readiness(
    runtime: Any,
    *,
    explicit_backend: LearningIngestRouteBackend | None = None,
) -> LearningIngestRouteBackendReadiness:
    backend = learning_ingest_route_backend_for_runtime(runtime, explicit_backend=explicit_backend)
    return LearningIngestRouteBackendReadiness(
        service_id=LEARNING_INGEST_SERVICE_ID,
        mode=getattr(backend, "mode", type(backend).__name__),
        ready=False,
        local_only=True,
        fallback_adapter="runtime.learning_service",
        rollback=LEARNING_INGEST_ROUTE_BACKEND_ROLLBACK,
        runtime_attr=LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR,
        contract_rollback=learning_ingest_contract().rollback,
        notes=(
            "disabled_by_default_contract_only",
            "dry_run_only_until_learning_state_writes_are_store_owned",
            "learning_ingest_remains_local_only",
        ),
    )


async def maybe_execute_learning_ingest_backend(
    runtime: Any,
    payload: dict[str, Any] | None,
    *,
    route: str,
    http_method: str,
    runtime_method: str,
    service_method: str,
) -> dict[str, Any] | None:
    if getattr(runtime, "_closed", False):
        return None
    if payload is not None and not isinstance(payload, dict):
        return None
    backend = learning_ingest_route_backend_for_runtime(runtime)
    if not bool(getattr(backend, "enabled", False)):
        return None
    request = LearningIngestRouteRequest(
        route=route,
        http_method=http_method,
        runtime_method=runtime_method,
        service_method=service_method,
        payload=dict(payload or {}),
    )
    return await backend.execute(runtime, request)
