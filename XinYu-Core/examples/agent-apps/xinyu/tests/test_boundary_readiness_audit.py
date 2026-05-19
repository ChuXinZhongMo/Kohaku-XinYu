from __future__ import annotations

from ops.validation.boundary_readiness_audit import (
    APP_ROOT,
    build_boundary_readiness_audit,
    generic_decision_count,
    render_markdown,
)


def test_boundary_readiness_audit_passes_for_current_boundaries() -> None:
    audit = build_boundary_readiness_audit(APP_ROOT.parents[3], app_root=APP_ROOT)

    assert audit["status"] == "pass"
    assert audit["manifest_failure_count"] == 0
    assert audit["reference_failure_count"] == 0
    assert audit["p0"]["generic_decision_count"] == 0
    assert audit["orphan_runtime_state_audit"]["held_orphan_count"] == 11


def test_generic_decision_count_counts_only_unresolved_decisions() -> None:
    assert generic_decision_count(
        {
            "migrate_candidate": 2,
            "manifested_private_runtime_queue": 1,
            "archive_candidate_after_caller_update": 3,
        }
    ) == 5


def test_boundary_readiness_markdown_is_body_safe() -> None:
    rendered = render_markdown(
        {
            "status": "pass",
            "manifest_count": 1,
            "manifest_failure_count": 0,
            "reference_audit_count": 1,
            "reference_failure_count": 0,
            "manifests": [
                {
                    "manifest_id": "sample_manifest",
                    "ok": True,
                    "check_count": 1,
                    "failure_count": 0,
                    "warning_count": 0,
                    "failures": [],
                }
            ],
            "reference_audits": [
                {
                    "audit_id": "sample_audit",
                    "status": "pass",
                    "item_count": 1,
                    "undeclared_reference_count": 0,
                }
            ],
            "orphan_runtime_state_audit": {
                "status": "review",
                "orphan_candidate_count": 9,
                "held_orphan_count": 9,
            },
            "p0": {
                "generic_decision_count": 0,
                "by_initial_decision": {"manifested_private_runtime_queue": 1},
                "generic_decisions": {},
            },
        }
    )

    assert "Boundary Readiness Audit" in rendered
    assert "does not read or print JSON/JSONL bodies" in rendered
    assert "sample_manifest" in rendered
