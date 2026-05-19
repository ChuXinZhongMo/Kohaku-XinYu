from __future__ import annotations

from ops.validation.validate_queue_boundary_manifest import validate_manifest, validate_queues


def test_default_queue_boundary_manifest_is_valid() -> None:
    result = validate_manifest()

    assert result.ok, result.failures
    queues = {check.queue_id: check for check in result.checks}
    assert queues["qq_outbox"].path == "memory/context/qq_outbox_queue.json"
    assert queues["qq_outbox"].retention_policy == "operational_queue"
    assert queues["qq_outbox"].status == "compat_runtime_queue"


def test_queue_boundary_manifest_rejects_body_migration_policy() -> None:
    result = validate_queues(
        [
            {
                "queue_id": "bad",
                "path": "memory/context/bad_queue.json",
                "owner_module": "xinyu_bad",
                "owner_symbols": ["write_bad"],
                "projection_paths": [],
                "allowed_raw_readers": ["xinyu_bad.py"],
                "privacy": "private_runtime_queue",
                "retention_policy": "operational_queue",
                "body_policy": "migrate_bodies",
                "stable_memory_policy": "runtime_queue_not_stable_memory",
                "status": "compat_runtime_queue",
            }
        ]
    )

    assert not result.ok
    assert any("invalid body_policy" in failure for failure in result.failures)


def test_queue_boundary_manifest_requires_owner_symbols() -> None:
    result = validate_queues(
        [
            {
                "queue_id": "bad",
                "path": "memory/context/bad_queue.json",
                "owner_module": "xinyu_bad",
                "owner_symbols": [],
                "projection_paths": [],
                "allowed_raw_readers": ["xinyu_bad.py"],
                "privacy": "private_runtime_queue",
                "retention_policy": "operational_queue",
                "body_policy": "no_body_migration",
                "stable_memory_policy": "runtime_queue_not_stable_memory",
                "status": "compat_runtime_queue",
            }
        ]
    )

    assert not result.ok
    assert any("owner_symbols must be a non-empty list" in failure for failure in result.failures)
