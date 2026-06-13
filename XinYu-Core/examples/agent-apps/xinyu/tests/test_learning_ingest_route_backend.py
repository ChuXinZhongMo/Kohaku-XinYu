from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from xinyu_bridge_learning_ingest_route_backend import (
    LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR,
    LEARNING_INGEST_ROUTE_BACKEND_ROLLBACK,
    DryRunLearningIngestRouteBackend,
    learning_ingest_route_backend_readiness,
    maybe_execute_learning_ingest_backend,
)
from xinyu_bridge_learning_ingest_contract import (
    learning_ingest_contract,
    learning_ingest_local_utility_route_map,
    learning_ingest_route_backend_route_map,
)
from xinyu_bridge_utility_routes import learning_ingest, learning_observe, learning_study
from xinyu_serviceization_contracts import service_contract_by_id


class FakeLearningService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("ingest", payload))
        return {"route": "ingest", "payload": payload}

    async def study(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("study", payload))
        return {"route": "study", "payload": payload}

    async def observe(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("observe", payload))
        return {"route": "observe", "payload": payload}


def test_learning_ingest_route_backend_contract_matches_service_manifest() -> None:
    manifest = service_contract_by_id("learning_ingest")

    assert "xinyu_bridge_learning_ingest_route_backend.py" in manifest.contract_modules
    assert "tests/test_learning_ingest_route_backend.py" in manifest.validation_tests
    assert manifest.process_split_candidate is False
    assert manifest.process_split_ready is False
    assert learning_ingest_route_backend_route_map() == {
        "/learning/ingest": "learning_ingest",
        "/learning/study": "learning_study",
        "/learning/observe": "learning_observe",
    }
    assert learning_ingest_local_utility_route_map() == {
        "/sticker/import": "sticker_import",
    }


def test_learning_ingest_route_backend_default_does_not_intercept() -> None:
    runtime = SimpleNamespace(_closed=False)

    result = asyncio.run(
        maybe_execute_learning_ingest_backend(
            runtime,
            {"file_path": "example.md"},
            route="/learning/ingest",
            http_method="POST",
            runtime_method="learning_ingest",
            service_method="ingest",
        )
    )
    readiness = learning_ingest_route_backend_readiness(runtime)
    contract = learning_ingest_contract()

    assert result is None
    assert readiness.service_id == "learning_ingest"
    assert readiness.ready is False
    assert readiness.local_only is True
    assert readiness.runtime_attr == LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR
    assert readiness.rollback == LEARNING_INGEST_ROUTE_BACKEND_ROLLBACK
    assert readiness.contract_rollback == contract.rollback
    assert readiness.rollback != readiness.contract_rollback
    assert "disabled_by_default_contract_only" in readiness.notes


def test_learning_ingest_routes_use_enabled_backend_without_calling_learning_service() -> None:
    service = FakeLearningService()
    runtime = SimpleNamespace(
        _closed=False,
        learning_service=service,
        **{LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR: DryRunLearningIngestRouteBackend(enabled=True)},
    )

    ingest = asyncio.run(learning_ingest(runtime, {"file_path": "example.md"}))
    study = asyncio.run(learning_study(runtime, {"mode": "quick"}))
    observe = asyncio.run(learning_observe(runtime, {"text": "note"}))

    assert ingest["request"]["route"] == "/learning/ingest"
    assert ingest["request"]["runtime_method"] == "learning_ingest"
    assert ingest["request"]["service_method"] == "ingest"
    assert study["request"]["route"] == "/learning/study"
    assert observe["request"]["route"] == "/learning/observe"
    assert service.calls == []


def test_learning_ingest_route_backend_rollback_restores_learning_service() -> None:
    service = FakeLearningService()
    runtime = SimpleNamespace(
        _closed=False,
        learning_service=service,
        **{LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR: DryRunLearningIngestRouteBackend(enabled=True)},
    )

    intercepted = asyncio.run(learning_ingest(runtime, {"file_path": "example.md"}))
    delattr(runtime, LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR)
    fallback = asyncio.run(learning_ingest(runtime, {"file_path": "example.md"}))

    assert intercepted["status"] == "dry_run_ready"
    assert fallback == {"route": "ingest", "payload": {"file_path": "example.md"}}
    assert service.calls == [("ingest", {"file_path": "example.md"})]
