from __future__ import annotations

import json

import state_service
from xinyu_bridge_state_persistence_contract import (
    STATE_PERSISTENCE_FALLBACK_ADAPTER,
    STATE_PERSISTENCE_OWNER,
    STATE_PERSISTENCE_ROLLBACK,
    StatePersistenceLocalHarness,
    state_persistence_contract,
    state_persistence_default_local_adapters,
    state_persistence_fallback_adapter,
    state_persistence_local_adapter_ids,
)
from xinyu_serviceization_contracts import (
    process_split_candidates,
    service_contract_by_id,
)


def test_state_persistence_contract_freezes_local_only_boundary() -> None:
    contract = state_persistence_contract()

    assert contract.service_id == "state_persistence"
    assert contract.local_only is True
    assert contract.process_split_candidate is False
    assert contract.process_split_ready is False
    assert contract.state_owner == STATE_PERSISTENCE_OWNER
    assert contract.owner_layer == "persistence"
    assert contract.public_api_routes == ()
    assert contract.public_runtime_facade_methods == ()
    assert state_persistence_local_adapter_ids() == (
        "atomic_write_json",
        "atomic_write_text",
        "append_jsonl",
        "read_json",
        "read_text_safe",
    )
    assert "protected_memory_writes_remain_behind_existing_review_gates" in contract.protected_gates
    assert "runtime_queue_state" in contract.runtime_queues_and_traces
    assert contract.fallback_adapter == STATE_PERSISTENCE_FALLBACK_ADAPTER
    assert "no_public_runtime_facade" in contract.fallback_adapter
    assert "existing in-process JSON/text state writers unchanged" in contract.rollback
    assert contract.harness == "StatePersistenceLocalHarness"


def test_state_persistence_contract_matches_service_boundary_manifest() -> None:
    contract = state_persistence_contract()
    manifest = service_contract_by_id("state_persistence")

    assert manifest.service_id == contract.service_id
    assert manifest.local_owner == contract.state_owner
    assert manifest.owner_layer == contract.owner_layer
    assert manifest.api_routes == contract.public_api_routes
    assert manifest.runtime_facade_methods == contract.public_runtime_facade_methods
    assert manifest.process_split_candidate is contract.process_split_candidate
    assert manifest.process_split_ready is contract.process_split_ready
    assert manifest.process_split_gate.startswith("Persistence boundary must consolidate writes locally")
    assert "state_persistence" not in {item.service_id for item in process_split_candidates()}


def test_state_persistence_fallback_adapter_is_local_only() -> None:
    calls: list[str] = []

    def _adapter(name: str):
        def call(*args, **kwargs):
            calls.append(name)
            return {"adapter": name, "args": args, "kwargs": kwargs}

        return call

    local_adapters = {
        adapter_id: _adapter(adapter_id)
        for adapter_id in state_persistence_local_adapter_ids()
    }
    local_adapters["chat"] = _adapter("chat")
    local_adapters["runtime_facade_methods"] = _adapter("runtime_facade_methods")

    fallback = state_persistence_fallback_adapter(local_adapters)

    assert set(fallback) == set(state_persistence_local_adapter_ids())
    assert "chat" not in fallback
    assert "runtime_facade_methods" not in fallback
    assert fallback["atomic_write_text"]("state/example.txt", "ok")["adapter"] == "atomic_write_text"
    assert calls == ["atomic_write_text"]


def test_state_persistence_harness_lifecycle_readiness() -> None:
    adapters = {
        adapter_id: (lambda *args, **kwargs: None)
        for adapter_id in state_persistence_local_adapter_ids()
    }
    harness = StatePersistenceLocalHarness(adapters)

    initial = harness.readiness()
    assert initial.service_id == "state_persistence"
    assert initial.mode == "local_consolidation_only"
    assert initial.started is False
    assert initial.ready is False
    assert initial.local_only is True
    assert initial.process_split_candidate is False
    assert initial.process_split_ready is False
    assert initial.state_owner == STATE_PERSISTENCE_OWNER
    assert initial.fallback_adapter == STATE_PERSISTENCE_FALLBACK_ADAPTER
    assert initial.rollback == STATE_PERSISTENCE_ROLLBACK
    assert initial.missing_local_adapters == ()
    assert initial.public_runtime_facade_methods == ()
    assert "no_public_runtime_facade" in initial.notes

    started = harness.start()
    assert started.started is True
    assert started.ready is True

    assert set(harness.fallback_adapter()) == set(state_persistence_local_adapter_ids())

    stopped = harness.stop()
    assert stopped.started is False
    assert stopped.ready is False


def test_state_persistence_harness_binds_default_local_state_service_adapters(tmp_path) -> None:
    harness = StatePersistenceLocalHarness()

    started = harness.start()
    assert started.ready is True
    assert started.missing_local_adapters == ()

    adapters = harness.fallback_adapter()
    assert set(adapters) == set(state_persistence_local_adapter_ids())

    json_path = tmp_path / "nested" / "state.json"
    text_path = tmp_path / "nested" / "state.txt"
    jsonl_path = tmp_path / "nested" / "trace.jsonl"
    missing_json_path = tmp_path / "nested" / "missing.json"
    bad_json_path = tmp_path / "nested" / "bad.json"

    adapters["atomic_write_json"](json_path, {"b": 2, "a": 1}, indent=None)
    assert adapters["read_json"](json_path) == {"a": 1, "b": 2}

    adapters["atomic_write_text"](text_path, "ready", final_newline=False)
    assert text_path.read_text(encoding="utf-8") == "ready"
    assert adapters["read_text_safe"](text_path) == "ready"
    assert adapters["read_text_safe"](tmp_path / "missing.txt", default="fallback") == "fallback"

    adapters["append_jsonl"](jsonl_path, {"b": 2, "a": 1})
    adapters["append_jsonl"](jsonl_path, {"event": "next"})
    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == [
        {"a": 1, "b": 2},
        {"event": "next"},
    ]

    bad_json_path.write_text("{bad", encoding="utf-8")
    assert adapters["read_json"](missing_json_path, default={"missing": True}) == {"missing": True}
    assert adapters["read_json"](bad_json_path, default={"bad": True}) == {"bad": True}


def test_state_persistence_default_local_adapters_match_contract_ids() -> None:
    adapters = state_persistence_default_local_adapters()

    assert set(adapters) == set(state_persistence_local_adapter_ids())
    assert all(callable(adapter) for adapter in adapters.values())
    assert adapters == {
        "atomic_write_json": state_service.atomic_write_json,
        "atomic_write_text": state_service.atomic_write_text,
        "append_jsonl": state_service.append_jsonl,
        "read_json": state_service.read_json,
        "read_text_safe": state_service.read_text_safe,
    }


def test_state_persistence_harness_reports_missing_local_adapters() -> None:
    harness = StatePersistenceLocalHarness({"atomic_write_json": lambda *args, **kwargs: None})

    started = harness.start()

    assert started.ready is False
    assert started.missing_local_adapters == (
        "atomic_write_text",
        "append_jsonl",
        "read_json",
        "read_text_safe",
    )
