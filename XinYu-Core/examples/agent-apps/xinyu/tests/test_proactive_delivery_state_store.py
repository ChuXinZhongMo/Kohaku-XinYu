from __future__ import annotations

from pathlib import Path

from xinyu_bridge_proactive_delivery_state_store import (
    PROACTIVE_DELIVERY_STATE_STORE_OWNER,
    PROACTIVE_DELIVERY_STATE_STORE_ROLLBACK,
    LocalProactiveDeliveryStateStore,
    ProactiveDeliveryStateStoreHarness,
    proactive_delivery_state_paths,
    proactive_delivery_state_store_adapter_ids,
    proactive_delivery_state_store_contract,
)
from xinyu_serviceization_contracts import service_contract_by_id


def test_proactive_delivery_state_store_contract_matches_service_boundary_manifest() -> None:
    contract = proactive_delivery_state_store_contract()
    manifest = service_contract_by_id("proactive_delivery")

    assert contract.service_id == "proactive_delivery"
    assert contract.owner == PROACTIVE_DELIVERY_STATE_STORE_OWNER
    assert "memory/context/proactive_request_state.md" in contract.state_files
    assert "memory/context/proactive_qq_dispatch_state.md" in contract.state_files
    assert "memory/context/qq_outbox_queue.json" in contract.queue_files
    assert "memory/context/.qq_outbox_queue.lock" in contract.queue_files
    assert proactive_delivery_state_store_adapter_ids() == (
        "paths",
        "read_text",
        "write_text",
        "read_outbox_queue",
        "write_outbox_queue",
    )
    assert "xinyu_bridge_proactive_delivery_state_store.py" in manifest.contract_modules
    assert "tests/test_proactive_delivery_state_store.py" in manifest.validation_tests
    assert manifest.process_split_ready is True
    assert "local state-store ownership" in manifest.process_split_gate


def test_proactive_delivery_state_paths_preserve_legacy_files(tmp_path: Path) -> None:
    paths = proactive_delivery_state_paths(tmp_path)

    assert paths.proactive_request_state == tmp_path / "memory/context/proactive_request_state.md"
    assert paths.proactive_dispatch_state == tmp_path / "memory/context/proactive_qq_dispatch_state.md"
    assert paths.proactive_presence_state == tmp_path / "memory/context/proactive_presence_state.md"
    assert paths.qq_outbox_queue == tmp_path / "memory/context/qq_outbox_queue.json"
    assert paths.qq_outbox_dispatch_state == tmp_path / "memory/context/qq_outbox_dispatch_state.md"
    assert paths.qq_outbox_lock == tmp_path / "memory/context/.qq_outbox_queue.lock"


def test_local_proactive_delivery_state_store_reads_and_writes_state_files(tmp_path: Path) -> None:
    store = LocalProactiveDeliveryStateStore(tmp_path)
    paths = store.paths()

    store.write_text(paths.proactive_request_state, "- status: sent")
    store.write_text(paths.proactive_dispatch_state, "- last_claim_status: sent")
    store.write_outbox_queue({"version": 1, "items": [{"id": "message-1", "status": "sent"}]})

    assert store.read_text(paths.proactive_request_state) == "- status: sent\n"
    assert store.read_text(paths.proactive_dispatch_state) == "- last_claim_status: sent\n"
    assert store.read_outbox_queue({}) == {
        "version": 1,
        "items": [{"id": "message-1", "status": "sent"}],
    }
    assert store.read_text(paths.proactive_presence_state) == ""


def test_proactive_delivery_state_store_harness_lifecycle_readiness(tmp_path: Path) -> None:
    harness = ProactiveDeliveryStateStoreHarness(tmp_path)

    initial = harness.readiness()
    assert initial.service_id == "proactive_delivery"
    assert initial.started is False
    assert initial.ready is False
    assert initial.owner == PROACTIVE_DELIVERY_STATE_STORE_OWNER
    assert initial.rollback == PROACTIVE_DELIVERY_STATE_STORE_ROLLBACK
    assert initial.missing_local_adapters == ()

    started = harness.start()
    assert started.started is True
    assert started.ready is True
    assert "no_external_state_service_started" in started.notes

    fallback = harness.fallback_adapter()
    assert set(fallback) == set(proactive_delivery_state_store_adapter_ids())
    assert fallback["paths"]().qq_outbox_queue == tmp_path / "memory/context/qq_outbox_queue.json"

    stopped = harness.stop()
    assert stopped.started is False
    assert stopped.ready is False


def test_proactive_delivery_state_store_harness_reports_missing_adapters(tmp_path: Path) -> None:
    harness = ProactiveDeliveryStateStoreHarness(
        tmp_path,
        local_adapters={"paths": lambda: proactive_delivery_state_paths(tmp_path)},
    )

    started = harness.start()

    assert started.ready is False
    assert started.missing_local_adapters == (
        "read_text",
        "write_text",
        "read_outbox_queue",
        "write_outbox_queue",
    )
