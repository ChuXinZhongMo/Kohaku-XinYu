from __future__ import annotations

from ops.validation.validate_runtime_trace_manifest import validate_manifest, validate_traces


def test_default_runtime_trace_manifest_is_valid() -> None:
    result = validate_manifest()

    assert result.ok, result.failures
    traces = {check.trace_id: check for check in result.checks}
    assert traces["impulse_soup"].path == "memory/context/impulse_soup_trace.jsonl"
    assert traces["impulse_soup"].retention_policy == "append_only_pending_rotation"
    assert traces["impulse_soup"].status == "compat_runtime_trace"
    assert traces["early_visible_segment_shadow"].path == "runtime/early_visible_segment_shadow.jsonl"
    assert traces["early_visible_segment_shadow"].status == "compat_runtime_trace"


def test_runtime_trace_manifest_rejects_body_migration_policy() -> None:
    result = validate_traces(
        [
            {
                "trace_id": "bad",
                "path": "memory/context/bad_trace.jsonl",
                "owner_module": "xinyu_bad",
                "owner_symbol": "write_bad",
                "projection_paths": [],
                "allowed_raw_readers": ["xinyu_bad.py"],
                "privacy": "internal_runtime_trace",
                "retention_policy": "append_only_pending_rotation",
                "body_policy": "migrate_bodies",
                "stable_memory_policy": "runtime_trace_not_stable_memory",
                "status": "compat_runtime_trace",
            }
        ]
    )

    assert not result.ok
    assert any("invalid body_policy" in failure for failure in result.failures)


def test_runtime_trace_manifest_rejects_paths_outside_runtime_boundaries() -> None:
    result = validate_traces(
        [
            {
                "trace_id": "bad",
                "path": "library/bad_trace.jsonl",
                "owner_module": "xinyu_bad",
                "owner_symbol": "write_bad",
                "projection_paths": [],
                "allowed_raw_readers": ["xinyu_bad.py"],
                "privacy": "internal_runtime_trace",
                "retention_policy": "append_only_pending_rotation",
                "body_policy": "no_body_migration",
                "stable_memory_policy": "runtime_trace_not_stable_memory",
                "status": "compat_runtime_trace",
            }
        ]
    )

    assert not result.ok
    assert any("path must be a relative memory/*.jsonl or runtime/*.jsonl path" in failure for failure in result.failures)
