from __future__ import annotations

from ops.validation.validate_event_boundary_manifest import (
    validate_manifest,
    validate_streams,
)


def test_default_event_boundary_manifest_is_valid() -> None:
    result = validate_manifest()

    assert result.ok, result.failures
    streams = {check.stream_id: check for check in result.checks}
    assert streams["interaction_journal"].path == "memory/context/interaction_journal.jsonl"
    assert streams["interaction_journal"].max_rows == 240
    assert streams["proactive_request_history"].path == "memory/context/proactive_request_history.jsonl"
    assert streams["owner_recent_events"].privacy == "private_relationship_event_log"


def test_event_boundary_manifest_rejects_body_migration_policy() -> None:
    result = validate_streams(
        [
            {
                "stream_id": "bad",
                "path": "memory/context/bad.jsonl",
                "owner_module": "xinyu_bad",
                "owner_symbol": "write_bad",
                "projection_paths": [],
                "allowed_raw_readers": ["xinyu_bad.py"],
                "privacy": "private_runtime_event_log",
                "retention_policy": "bounded_rows",
                "max_rows": 10,
                "body_policy": "migrate_bodies",
                "stable_memory_policy": "runtime_not_memory",
                "status": "compat_event_stream",
            }
        ]
    )

    assert not result.ok
    assert any("invalid body_policy" in failure for failure in result.failures)


def test_event_boundary_manifest_rejects_unbounded_rows() -> None:
    result = validate_streams(
        [
            {
                "stream_id": "bad",
                "path": "memory/context/bad.jsonl",
                "owner_module": "xinyu_bad",
                "owner_symbol": "write_bad",
                "projection_paths": [],
                "allowed_raw_readers": ["xinyu_bad.py"],
                "privacy": "private_runtime_event_log",
                "retention_policy": "bounded_rows",
                "max_rows": 0,
                "body_policy": "no_body_migration",
                "stable_memory_policy": "runtime_not_memory",
                "status": "compat_event_stream",
            }
        ]
    )

    assert not result.ok
    assert any("max_rows must be positive" in failure for failure in result.failures)
