from __future__ import annotations

from xinyu_bridge_state_persistence_contract import state_persistence_local_adapter_ids
from xinyu_bridge_state_persistence_service import (
    STATE_PERSISTENCE_SERVICE_MODE_LOCAL,
    StatePersistenceServiceConfig,
    build_state_persistence_service_handle,
    state_persistence_service_readiness,
)


def _adapters():
    return {
        adapter_id: (lambda *args, **kwargs: None)
        for adapter_id in state_persistence_local_adapter_ids()
    }


def test_state_persistence_service_lifecycle_uses_local_contract_harness() -> None:
    handle = build_state_persistence_service_handle(local_adapters=_adapters())

    initial = handle.readiness()
    started = handle.start()
    closed = handle.close()

    assert handle.config == StatePersistenceServiceConfig(mode=STATE_PERSISTENCE_SERVICE_MODE_LOCAL)
    assert initial.service_id == "state_persistence"
    assert initial.started is False
    assert initial.ready is False
    assert started.started is True
    assert started.ready is True
    assert started.local_only is True
    assert started.process_split_candidate is False
    assert started.process_split_ready is False
    assert started.public_runtime_facade_methods == ()
    assert started.missing_local_adapters == ()
    assert closed.started is False
    assert closed.ready is False


def test_state_persistence_service_exposes_only_local_fallback_adapters() -> None:
    handle = build_state_persistence_service_handle(local_adapters=_adapters())

    adapters = handle.fallback_adapter()

    assert set(adapters) == set(state_persistence_local_adapter_ids())
    assert "chat" not in adapters
    assert "learning_ingest" not in adapters


def test_state_persistence_service_reports_missing_adapters() -> None:
    handle = build_state_persistence_service_handle(local_adapters={"atomic_write_json": lambda *args: None})

    readiness = handle.start()

    assert readiness.ready is False
    assert readiness.missing_local_adapters == (
        "atomic_write_text",
        "append_jsonl",
        "read_json",
        "read_text_safe",
    )


def test_state_persistence_service_readiness_helper_uses_runtime_handle() -> None:
    class Runtime:
        pass

    runtime = Runtime()
    runtime._state_persistence_service = build_state_persistence_service_handle(local_adapters=_adapters())
    runtime._state_persistence_service.start()

    assert state_persistence_service_readiness(runtime).ready is True
