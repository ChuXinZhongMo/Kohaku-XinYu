from __future__ import annotations

from ops.validation.validate_memory_library_manifest import (
    is_sensitive_deny_path,
    validate_entries,
    validate_manifest,
)


def test_default_memory_library_manifest_is_valid() -> None:
    result = validate_manifest()

    assert result.ok, result.failures
    paths = {check.path: check for check in result.checks}
    assert paths["memory"].include_policy == "redact"
    assert paths["data/external"].status == "ok"
    assert paths["runtime"].include_policy == "exclude"
    assert paths["logs"].include_policy == "exclude"


def test_sensitive_runtime_paths_cannot_be_included() -> None:
    assert is_sensitive_deny_path("runtime/dialogue_archive")
    result = validate_entries(
        [
            {
                "path": "runtime/dialogue_archive",
                "category": "runtime",
                "tier": "traces",
                "include_policy": "include",
                "sensitivity": "high",
                "source_type": "runtime_generated",
                "license_or_consent": "owner_private_local",
                "retention_days": 14,
                "contains_pii": True,
                "requires_redaction": False,
                "max_file_count": 10,
                "snapshot_allowed": True,
                "last_verified_at": "2026-05-17",
                "verifier_version": "test",
            }
        ]
    )

    assert not result.ok
    assert any("denylisted path cannot be directly included" in failure for failure in result.failures)
    assert any("PII paths cannot allow snapshots" in failure for failure in result.failures)
