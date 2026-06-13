from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


LIFE_METABOLISM_STATE_OWNER = "self_choice_metabolism_ticket_ledger_and_runtime_runner_state"
LIFE_METABOLISM_FALLBACK_ADAPTER = "in_process_life_metabolism_runtime_facade_methods"
LIFE_METABOLISM_ROLLBACK = "keep_life_metabolism_on_current_local_runtime_facades"


@dataclass(frozen=True, slots=True)
class LifeMetabolismCapability:
    route: str
    http_method: str
    runtime_method: str
    contract: str


@dataclass(frozen=True, slots=True)
class LifeMetabolismReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    api_routes: tuple[str, ...]
    route_templates: tuple[str, ...]
    runtime_facade_methods: tuple[str, ...]
    route_backend_routes: tuple[str, ...]
    ticket_action_routes: tuple[str, ...]
    dynamic_ticket_routes: bool
    state_owner: str
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


LIFE_METABOLISM_CAPABILITIES = (
    LifeMetabolismCapability(
        route="/life/metabolism/tickets/{ticket_id}",
        http_method="GET",
        runtime_method="life_metabolism_ticket_get",
        contract="read a local self-choice metabolism ticket by id",
    ),
    LifeMetabolismCapability(
        route="/life/metabolism/tickets",
        http_method="GET",
        runtime_method="life_metabolism_ticket_list",
        contract="list local self-choice metabolism tickets for owner-visible review",
    ),
    LifeMetabolismCapability(
        route="/life/metabolism/tickets/{ticket_id}/approve",
        http_method="POST",
        runtime_method="life_metabolism_ticket_approve",
        contract="approve a local self-choice metabolism ticket and wake the in-process runner",
    ),
    LifeMetabolismCapability(
        route="/life/metabolism/tickets/{ticket_id}/reject",
        http_method="POST",
        runtime_method="life_metabolism_ticket_reject",
        contract="reject a local self-choice metabolism ticket through the current policy path",
    ),
    LifeMetabolismCapability(
        route="/life/metabolism/tickets/{ticket_id}/cancel",
        http_method="POST",
        runtime_method="life_metabolism_ticket_cancel",
        contract="cancel a local self-choice metabolism ticket through the current policy path",
    ),
)


class LifeMetabolismHarness:
    def __init__(self) -> None:
        self._started = False

    def start(self) -> LifeMetabolismReadiness:
        self._started = True
        return self.readiness()

    def stop(self) -> LifeMetabolismReadiness:
        self._started = False
        return self.readiness()

    def readiness(self) -> LifeMetabolismReadiness:
        return LifeMetabolismReadiness(
            service_id="life_metabolism",
            mode="local_only_in_process",
            started=self._started,
            ready=self._started,
            api_routes=life_metabolism_routes(),
            route_templates=life_metabolism_route_templates(),
            runtime_facade_methods=life_metabolism_runtime_methods(),
            route_backend_routes=life_metabolism_route_backend_routes(),
            ticket_action_routes=life_metabolism_ticket_action_routes(),
            dynamic_ticket_routes=True,
            state_owner=LIFE_METABOLISM_STATE_OWNER,
            fallback_adapter=LIFE_METABOLISM_FALLBACK_ADAPTER,
            rollback=LIFE_METABOLISM_ROLLBACK,
            notes=(
                "self_choice_policy_desktop_visibility_and_runtime_lifecycle_remain_coupled",
                "harness_contract_only_no_process_split_candidate",
                "dynamic_ticket_routes_remain_in_process",
            ),
        )

    @staticmethod
    def fallback_adapter(runtime: Any) -> dict[str, Callable[..., Any]]:
        return {method: getattr(runtime, method) for method in life_metabolism_runtime_methods()}


def life_metabolism_capabilities() -> tuple[LifeMetabolismCapability, ...]:
    return LIFE_METABOLISM_CAPABILITIES


def life_metabolism_routes() -> tuple[str, ...]:
    seen: set[str] = set()
    routes: list[str] = []
    for capability in LIFE_METABOLISM_CAPABILITIES:
        route = _manifest_route(capability.route)
        if route in seen:
            continue
        seen.add(route)
        routes.append(route)
    return tuple(routes)


def life_metabolism_route_templates() -> tuple[str, ...]:
    return tuple(capability.route for capability in LIFE_METABOLISM_CAPABILITIES)


def life_metabolism_route_backend_routes() -> tuple[str, ...]:
    return life_metabolism_route_templates()


def life_metabolism_ticket_action_routes() -> tuple[str, ...]:
    return tuple(
        capability.route
        for capability in LIFE_METABOLISM_CAPABILITIES
        if capability.http_method == "POST"
    )


def life_metabolism_runtime_methods() -> tuple[str, ...]:
    seen: set[str] = set()
    methods: list[str] = []
    for capability in LIFE_METABOLISM_CAPABILITIES:
        if capability.runtime_method in seen:
            continue
        seen.add(capability.runtime_method)
        methods.append(capability.runtime_method)
    return tuple(methods)


def _manifest_route(route: str) -> str:
    return "/life/metabolism/tickets" if route.startswith("/life/metabolism/tickets/") else route
