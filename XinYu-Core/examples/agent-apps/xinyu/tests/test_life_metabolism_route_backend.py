from __future__ import annotations

import asyncio
from types import SimpleNamespace

from xinyu_bridge_life_metabolism_route_backend import (
    LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR,
    LIFE_METABOLISM_ROUTE_BACKEND_ROLLBACK,
    DryRunLifeMetabolismRouteBackend,
    life_metabolism_route_backend_readiness,
    maybe_execute_life_metabolism_backend,
)
from xinyu_bridge_life_metabolism_contract import LIFE_METABOLISM_ROLLBACK
from xinyu_bridge_life_metabolism_contract import life_metabolism_route_backend_routes
from xinyu_bridge_metabolism_routes import (
    life_metabolism_ticket_approve,
    life_metabolism_ticket_cancel,
    life_metabolism_ticket_get,
    life_metabolism_ticket_list,
    life_metabolism_ticket_reject,
)
from xinyu_serviceization_contracts import service_contract_by_id


def test_life_metabolism_route_backend_contract_matches_service_manifest() -> None:
    manifest = service_contract_by_id("life_metabolism")

    assert "xinyu_bridge_life_metabolism_route_backend.py" in manifest.contract_modules
    assert "tests/test_life_metabolism_route_backend.py" in manifest.validation_tests
    assert manifest.process_split_candidate is False
    assert manifest.process_split_ready is False
    assert life_metabolism_route_backend_routes() == (
        "/life/metabolism/tickets/{ticket_id}",
        "/life/metabolism/tickets",
        "/life/metabolism/tickets/{ticket_id}/approve",
        "/life/metabolism/tickets/{ticket_id}/reject",
        "/life/metabolism/tickets/{ticket_id}/cancel",
    )


def test_life_metabolism_route_backend_default_does_not_intercept() -> None:
    runtime = SimpleNamespace()

    result = asyncio.run(
        maybe_execute_life_metabolism_backend(
            runtime,
            {"ticket_id": "ticket-1"},
            route="/life/metabolism/tickets/{ticket_id}",
            http_method="GET",
            runtime_method="life_metabolism_ticket_get",
        )
    )
    readiness = life_metabolism_route_backend_readiness(runtime)

    assert result is None
    assert readiness.service_id == "life_metabolism"
    assert readiness.local_only is True
    assert readiness.ready is False
    assert readiness.runtime_attr == LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR
    assert readiness.rollback == LIFE_METABOLISM_ROUTE_BACKEND_ROLLBACK
    assert readiness.contract_rollback == LIFE_METABOLISM_ROLLBACK
    assert readiness.rollback != readiness.contract_rollback
    assert "disabled_by_default_contract_only" in readiness.notes


def test_life_metabolism_routes_use_enabled_backend() -> None:
    runtime = SimpleNamespace(
        **{LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR: DryRunLifeMetabolismRouteBackend(enabled=True)}
    )

    listed = asyncio.run(life_metabolism_ticket_list(runtime, {"status": "requested"}))
    found = asyncio.run(life_metabolism_ticket_get(runtime, {"ticket_id": "ticket-1"}))
    approved = asyncio.run(life_metabolism_ticket_approve(runtime, {"ticket_id": "ticket-1"}))
    rejected = asyncio.run(life_metabolism_ticket_reject(runtime, {"ticket_id": "ticket-1"}))
    cancelled = asyncio.run(life_metabolism_ticket_cancel(runtime, {"ticket_id": "ticket-1"}))

    assert listed["request"]["route"] == "/life/metabolism/tickets"
    assert listed["request"]["runtime_method"] == "life_metabolism_ticket_list"
    assert found["request"]["route"] == "/life/metabolism/tickets/{ticket_id}"
    assert approved["request"]["route"] == "/life/metabolism/tickets/{ticket_id}/approve"
    assert rejected["request"]["route"] == "/life/metabolism/tickets/{ticket_id}/reject"
    assert cancelled["request"]["route"] == "/life/metabolism/tickets/{ticket_id}/cancel"
    assert all(result["executed"] is False for result in (listed, found, approved, rejected, cancelled))


def test_life_metabolism_route_backend_rollback_restores_current_facade(monkeypatch, tmp_path) -> None:
    calls: list[tuple[object, object]] = []
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        **{LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR: DryRunLifeMetabolismRouteBackend(enabled=True)},
    )

    def list_tickets(root, *, statuses):
        calls.append((root, statuses))
        return [{"ticket_id": "ticket-1"}]

    monkeypatch.setattr("xinyu_bridge_metabolism_routes.list_metabolism_tickets", list_tickets)

    intercepted = asyncio.run(life_metabolism_ticket_list(runtime, {}))
    delattr(runtime, LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR)
    fallback = asyncio.run(life_metabolism_ticket_list(runtime, {}))

    assert intercepted["status"] == "dry_run_ready"
    assert fallback == {"accepted": True, "tickets": [{"ticket_id": "ticket-1"}], "notes": ["tickets_listed"]}
    assert calls == [(tmp_path, None)]
