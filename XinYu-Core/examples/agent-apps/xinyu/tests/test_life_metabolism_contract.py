from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_http_dispatch_life_ticket import life_ticket_get_spec, life_ticket_post_spec
from xinyu_bridge_http_routes import (
    LIFE_TICKET_PREFIX,
    is_known_get_route,
    is_known_post_route,
    is_life_ticket_action_route,
    life_ticket_action,
    post_route_requires_bridge_token,
)
from xinyu_bridge_life_metabolism_contract import (
    LIFE_METABOLISM_FALLBACK_ADAPTER,
    LIFE_METABOLISM_ROLLBACK,
    LIFE_METABOLISM_STATE_OWNER,
    LifeMetabolismHarness,
    life_metabolism_capabilities,
    life_metabolism_route_backend_routes,
    life_metabolism_route_templates,
    life_metabolism_routes,
    life_metabolism_runtime_methods,
    life_metabolism_ticket_action_routes,
)
from xinyu_serviceization_contracts import (
    process_split_candidates,
    service_contract_by_id,
)
from xinyu_serviceization_readiness import assess_service_split_readiness


def test_life_metabolism_contract_matches_service_boundary_manifest() -> None:
    contract = service_contract_by_id("life_metabolism")

    assert life_metabolism_routes() == contract.api_routes
    assert life_metabolism_routes() == ("/life/metabolism/tickets",)
    assert life_metabolism_route_templates() == tuple(
        capability.route for capability in life_metabolism_capabilities()
    )
    assert life_metabolism_route_backend_routes() == life_metabolism_route_templates()
    assert life_metabolism_ticket_action_routes() == (
        "/life/metabolism/tickets/{ticket_id}/approve",
        "/life/metabolism/tickets/{ticket_id}/reject",
        "/life/metabolism/tickets/{ticket_id}/cancel",
    )
    assert life_metabolism_runtime_methods() == contract.runtime_facade_methods
    assert contract.process_split_candidate is False
    assert contract.process_split_ready is False
    assert "self-choice policy" in contract.process_split_gate
    assert "desktop visibility" in contract.process_split_gate
    assert "runtime lifecycle" in contract.process_split_gate


def test_life_metabolism_is_local_only_not_split_candidate() -> None:
    contract = service_contract_by_id("life_metabolism")
    readiness = assess_service_split_readiness(contract)

    assert "life_metabolism" not in {candidate.service_id for candidate in process_split_candidates()}
    assert readiness.service_id == "life_metabolism"
    assert readiness.candidate is False
    assert readiness.ready is False
    assert readiness.blockers[0] == "not_process_split_candidate"
    assert "Keep local" in readiness.blockers[1]


def test_life_metabolism_contract_matches_http_dispatch() -> None:
    payloads: dict[str, dict[str, str]] = {
        "GET:/life/metabolism/tickets": {},
        "GET:/life/metabolism/tickets/{ticket_id}": {},
        "POST:/life/metabolism/tickets/{ticket_id}/approve": {},
        "POST:/life/metabolism/tickets/{ticket_id}/reject": {},
        "POST:/life/metabolism/tickets/{ticket_id}/cancel": {},
    }

    for capability in life_metabolism_capabilities():
        route = capability.route.replace("{ticket_id}", "ticket-1")
        payload = payloads[f"{capability.http_method}:{capability.route}"]

        if capability.http_method == "GET":
            assert is_known_get_route(route)
            spec = life_ticket_get_spec(route, payload)
        else:
            assert capability.http_method == "POST"
            assert is_known_post_route(route)
            assert post_route_requires_bridge_token(route)
            spec = life_ticket_post_spec(
                route,
                payload,
                is_action_route_func=is_life_ticket_action_route,
                action_func=life_ticket_action,
            )

        assert spec is not None
        assert spec.method == capability.runtime_method

    assert payloads[f"GET:{LIFE_TICKET_PREFIX}/{{ticket_id}}"] == {"ticket_id": "ticket-1"}
    assert payloads[f"POST:{LIFE_TICKET_PREFIX}/{{ticket_id}}/approve"] == {"ticket_id": "ticket-1"}
    assert payloads[f"POST:{LIFE_TICKET_PREFIX}/{{ticket_id}}/reject"] == {"ticket_id": "ticket-1"}
    assert payloads[f"POST:{LIFE_TICKET_PREFIX}/{{ticket_id}}/cancel"] == {"ticket_id": "ticket-1"}


def test_life_metabolism_harness_lifecycle_readiness_and_fallback() -> None:
    harness = LifeMetabolismHarness()

    initial = harness.readiness()
    assert initial.service_id == "life_metabolism"
    assert initial.mode == "local_only_in_process"
    assert initial.started is False
    assert initial.ready is False
    assert initial.api_routes == life_metabolism_routes()
    assert initial.route_templates == life_metabolism_route_templates()
    assert initial.runtime_facade_methods == life_metabolism_runtime_methods()
    assert initial.route_backend_routes == life_metabolism_route_backend_routes()
    assert initial.ticket_action_routes == life_metabolism_ticket_action_routes()
    assert initial.dynamic_ticket_routes is True
    assert initial.state_owner == LIFE_METABOLISM_STATE_OWNER
    assert initial.fallback_adapter == LIFE_METABOLISM_FALLBACK_ADAPTER
    assert initial.rollback == LIFE_METABOLISM_ROLLBACK
    assert "harness_contract_only_no_process_split_candidate" in initial.notes
    assert "dynamic_ticket_routes_remain_in_process" in initial.notes

    started = harness.start()
    assert started.started is True
    assert started.ready is True

    calls: list[str] = []

    def _method(name: str):
        def call(*args, **kwargs):
            calls.append(name)
            return {"method": name, "args": args, "kwargs": kwargs}

        return call

    runtime = SimpleNamespace(**{method: _method(method) for method in life_metabolism_runtime_methods()})
    fallback = harness.fallback_adapter(runtime)

    assert set(fallback) == set(life_metabolism_runtime_methods())
    for method in life_metabolism_runtime_methods():
        assert fallback[method] is getattr(runtime, method)

    assert fallback["life_metabolism_ticket_list"]({"status": "requested"})["method"] == "life_metabolism_ticket_list"
    assert calls == ["life_metabolism_ticket_list"]

    stopped = harness.stop()
    assert stopped.started is False
    assert stopped.ready is False
