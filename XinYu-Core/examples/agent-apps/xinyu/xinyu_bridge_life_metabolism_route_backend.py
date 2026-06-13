from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from xinyu_bridge_life_metabolism_contract import (
    LIFE_METABOLISM_FALLBACK_ADAPTER,
    LIFE_METABOLISM_ROLLBACK,
    LIFE_METABOLISM_STATE_OWNER,
)


LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR = "_life_metabolism_route_backend"
LIFE_METABOLISM_BACKEND_DISABLED_MODE = "disabled_contract_only_life_metabolism_route_backend"
LIFE_METABOLISM_BACKEND_DRY_RUN_MODE = "life_metabolism_route_backend_dry_run"
LIFE_METABOLISM_ROUTE_BACKEND_ROLLBACK = "remove_runtime_life_metabolism_backend_attr_to_use_current_facades"


@dataclass(frozen=True, slots=True)
class LifeMetabolismRouteRequest:
    route: str
    http_method: str
    runtime_method: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def dry_run_shape(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "http_method": self.http_method,
            "runtime_method": self.runtime_method,
            "payload": dict(self.payload),
        }


class LifeMetabolismRouteBackend(Protocol):
    mode: str

    async def execute(self, runtime: Any, request: LifeMetabolismRouteRequest) -> dict[str, Any]:
        ...


@dataclass(frozen=True, slots=True)
class LifeMetabolismRouteBackendReadiness:
    service_id: str
    mode: str
    ready: bool
    local_only: bool
    state_owner: str
    fallback_adapter: str
    rollback: str
    runtime_attr: str
    contract_rollback: str
    notes: tuple[str, ...] = ()


class DryRunLifeMetabolismRouteBackend:
    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = bool(enabled)
        self.mode = LIFE_METABOLISM_BACKEND_DRY_RUN_MODE if self.enabled else LIFE_METABOLISM_BACKEND_DISABLED_MODE

    async def execute(self, runtime: Any, request: LifeMetabolismRouteRequest) -> dict[str, Any]:
        return {
            "service_id": "life_metabolism",
            "status": "dry_run_ready" if self.enabled else "backend_disabled",
            "mode": self.mode,
            "enabled": self.enabled,
            "dry_run": True,
            "executed": False,
            "request": request.dry_run_shape(),
            "fallback_adapter": LIFE_METABOLISM_FALLBACK_ADAPTER,
            "rollback": LIFE_METABOLISM_ROUTE_BACKEND_ROLLBACK,
            "contract_rollback": LIFE_METABOLISM_ROLLBACK,
            "notes": (
                "contract_only_no_metabolism_ticket_state_mutated",
                "runtime_method_not_invoked",
                "self_choice_policy_remains_local",
            ),
        }


DISABLED_LIFE_METABOLISM_ROUTE_BACKEND = DryRunLifeMetabolismRouteBackend(enabled=False)


def life_metabolism_route_backend_for_runtime(
    runtime: Any,
    *,
    explicit_backend: LifeMetabolismRouteBackend | None = None,
) -> LifeMetabolismRouteBackend:
    if explicit_backend is not None:
        return explicit_backend
    runtime_backend = getattr(runtime, LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR, None)
    if runtime_backend is not None:
        return runtime_backend
    return DISABLED_LIFE_METABOLISM_ROUTE_BACKEND


def life_metabolism_route_backend_readiness(
    runtime: Any,
    *,
    explicit_backend: LifeMetabolismRouteBackend | None = None,
) -> LifeMetabolismRouteBackendReadiness:
    backend = life_metabolism_route_backend_for_runtime(runtime, explicit_backend=explicit_backend)
    return LifeMetabolismRouteBackendReadiness(
        service_id="life_metabolism",
        mode=getattr(backend, "mode", type(backend).__name__),
        ready=False,
        local_only=True,
        state_owner=LIFE_METABOLISM_STATE_OWNER,
        fallback_adapter=LIFE_METABOLISM_FALLBACK_ADAPTER,
        rollback=LIFE_METABOLISM_ROUTE_BACKEND_ROLLBACK,
        runtime_attr=LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR,
        contract_rollback=LIFE_METABOLISM_ROLLBACK,
        notes=(
            "disabled_by_default_contract_only",
            "dry_run_only_until_self_choice_policy_and_runner_state_are_store_owned",
            "life_metabolism_remains_local_only",
        ),
    )


async def maybe_execute_life_metabolism_backend(
    runtime: Any,
    payload: dict[str, Any] | None,
    *,
    route: str,
    http_method: str,
    runtime_method: str,
) -> dict[str, Any] | None:
    if payload is not None and not isinstance(payload, dict):
        return None
    backend = life_metabolism_route_backend_for_runtime(runtime)
    if not bool(getattr(backend, "enabled", False)):
        return None
    request = LifeMetabolismRouteRequest(
        route=route,
        http_method=http_method,
        runtime_method=runtime_method,
        payload=dict(payload or {}),
    )
    return await backend.execute(runtime, request)
