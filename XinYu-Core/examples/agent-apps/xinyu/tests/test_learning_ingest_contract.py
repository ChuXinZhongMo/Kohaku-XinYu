from __future__ import annotations

import asyncio
from typing import Any

from xinyu_bridge_http_dispatch_table import POST_ROUTE_DISPATCH
from xinyu_bridge_http_routes import is_known_post_route
from xinyu_bridge_learning_ingest_contract import (
    LearningIngestLocalHarness,
    learning_ingest_contract,
    learning_ingest_fallback_adapter,
    learning_ingest_local_utility_route_map,
    learning_ingest_route_backend_route_map,
    learning_ingest_route_map,
)
from xinyu_serviceization_contracts import (
    process_split_candidates,
    service_contract_by_id,
)


class _Runtime:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def learning_ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("learning_ingest", payload)

    async def learning_study(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("learning_study", payload)

    async def learning_observe(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("learning_observe", payload)

    async def sticker_import(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("sticker_import", payload)

    def _record(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, dict(payload)))
        return {"route": name, "payload": dict(payload)}


def test_learning_ingest_contract_freezes_local_only_boundary() -> None:
    contract = learning_ingest_contract()

    assert contract.service_id == "learning_ingest"
    assert contract.local_only is True
    assert contract.process_split_candidate is False
    assert contract.runtime_methods == (
        "learning_ingest",
        "learning_study",
        "learning_observe",
        "sticker_import",
    )
    assert learning_ingest_route_map() == {
        "/learning/ingest": "learning_ingest",
        "/learning/study": "learning_study",
        "/learning/observe": "learning_observe",
        "/sticker/import": "sticker_import",
    }
    assert learning_ingest_route_backend_route_map() == {
        "/learning/ingest": "learning_ingest",
        "/learning/study": "learning_study",
        "/learning/observe": "learning_observe",
    }
    assert learning_ingest_local_utility_route_map() == {
        "/sticker/import": "sticker_import",
    }
    assert "reviewed-memory gates" in contract.reviewed_memory_gate
    assert "runtime facade" in contract.fallback_adapter
    assert "trace-only" in contract.sidecar_ingest
    assert "keep existing local files" in contract.rollback


def test_learning_ingest_contract_aligns_with_service_boundary_manifest() -> None:
    contract = learning_ingest_contract()
    manifest = service_contract_by_id("learning_ingest")

    assert manifest.api_routes == tuple(learning_ingest_route_map())
    assert manifest.runtime_facade_methods == contract.runtime_methods
    assert manifest.process_split_candidate is False
    assert manifest.process_split_ready is False
    assert "reviewed-memory gates" in manifest.process_split_gate
    assert "learning_ingest" not in {item.service_id for item in process_split_candidates()}


def test_learning_ingest_contract_aligns_with_http_dispatch() -> None:
    for route, method in learning_ingest_route_map().items():
        assert is_known_post_route(route)
        assert POST_ROUTE_DISPATCH[route].method == method
        assert POST_ROUTE_DISPATCH[route].fast_method is None


def test_learning_ingest_harness_lifecycle_readiness_and_fallback() -> None:
    runtime = _Runtime()
    harness = LearningIngestLocalHarness(runtime)

    assert harness.readiness()["ready"] is False
    harness.start()
    ready = harness.readiness()
    assert ready["ready"] is True
    assert ready["local_only"] is True
    assert ready["process_split_candidate"] is False
    assert ready["missing_runtime_methods"] == ()
    assert ready["routes"] == learning_ingest_route_map()

    result = asyncio.run(harness.fallback("/learning/ingest", {"file_path": "learning/README.md"}))
    assert result == {
        "route": "learning_ingest",
        "payload": {"file_path": "learning/README.md"},
    }
    sticker = asyncio.run(harness.fallback("/sticker/import", {"source": "qq"}))
    assert sticker == {
        "route": "sticker_import",
        "payload": {"source": "qq"},
    }
    assert runtime.calls == [
        ("learning_ingest", {"file_path": "learning/README.md"}),
        ("sticker_import", {"source": "qq"}),
    ]

    harness.stop()
    assert harness.readiness()["ready"] is False


def test_learning_ingest_fallback_adapter_maps_only_current_runtime_facade_methods() -> None:
    runtime = _Runtime()
    adapter = learning_ingest_fallback_adapter(runtime)

    assert set(adapter) == set(learning_ingest_route_map())
    assert {route: method.__name__ for route, method in adapter.items()} == learning_ingest_route_map()
