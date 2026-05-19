from __future__ import annotations

from ops.validation.validate_orphan_runtime_state_manifest import validate_manifest, validate_states


def test_default_orphan_runtime_state_manifest_is_valid() -> None:
    result = validate_manifest()

    assert result.ok, result.failures
    paths = {check.path for check in result.checks}
    assert "memory/consolidation_state.json" in paths
    assert "memory/runtime_bridge_state.json" in paths
    assert all(check.delete_allowed is False for check in result.checks)


def test_orphan_runtime_state_manifest_rejects_delete_allowed() -> None:
    result = validate_states(
        [
            {
                "path": "memory/context/old_state.json",
                "decision": "held_orphan_runtime_state",
                "target_boundary": "stores/orphan_runtime_state_manifest",
                "delete_allowed": True,
                "handling": "Keep in place.",
            }
        ]
    )

    assert not result.ok
    assert any("delete_allowed must be false" in failure for failure in result.failures)


def test_orphan_runtime_state_manifest_rejects_wrong_decision() -> None:
    result = validate_states(
        [
            {
                "path": "memory/context/old_state.json",
                "decision": "delete_candidate",
                "target_boundary": "stores/orphan_runtime_state_manifest",
                "delete_allowed": False,
                "handling": "Keep in place.",
            }
        ]
    )

    assert not result.ok
    assert any("invalid decision" in failure for failure in result.failures)
