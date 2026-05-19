from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from commit_readiness_audit import build_commit_readiness_audit, render_markdown  # noqa: E402
from git_change_group_audit import parse_short_status  # noqa: E402


PASSING_BOUNDARY = {
    "status": "pass",
    "manifest_failure_count": 0,
    "reference_failure_count": 0,
    "p0": {"generic_decision_count": 0},
    "orphan_runtime_state_audit": {"held_orphan_count": 0},
}

EMPTY_ARCHIVE = {
    "total_candidates": 0,
    "by_decision": {},
    "by_kind": {},
}


def test_commit_readiness_groups_packages_and_status() -> None:
    entries = parse_short_status(
        " M plan-next-9.md\n"
        " M XinYu-Core/examples/agent-apps/xinyu/custom/source_gate_engine.py\n"
        " M XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_gateway_context_enrichment.py\n"
        " M XinYu_Desktop/src/main/api_config.ts\n"
        " M XinYu-Core/examples/agent-apps/xinyu/memory-seeds/README.md\n"
        " D XinYu-Core/examples/agent-apps/xinyu/context_retrieval_smoke.py\n"
    )
    archive = {
        "total_candidates": 1,
        "by_decision": {"accept_delete_relocated": 1},
        "by_kind": {"root_smoke": 1},
    }

    audit = build_commit_readiness_audit(
        Path("D:/XinYu"),
        entries=entries,
        boundary_audit=PASSING_BOUNDARY,
        archive_delete_audit=archive,
    )

    assert audit["status"] == "ready_for_review"
    assert audit["unknown_entry_count"] == 0
    assert audit["archive_delete"]["hold_count"] == 0
    assert audit["closeout_summary"]["archived"] == ["1 cleanup deletions have relocated replacements."]
    by_id = {package["id"]: package for package in audit["package_overview"]}
    assert by_id["P03"]["review_action"] == "merge_review_core_runtime"
    assert by_id["P04"]["review_action"] == "merge_review_adapters"
    assert by_id["P06"]["review_action"] == "keep_memory_data_review_only"


def test_commit_readiness_holds_unknown_and_archive_refs() -> None:
    entries = parse_short_status(
        " M unmatched/path.txt\n"
        " D XinYu-Core/examples/agent-apps/xinyu/check_runtime_env.py\n"
    )
    archive = {
        "total_candidates": 1,
        "by_decision": {"hold_delete_referenced": 1},
        "by_kind": {"root_diagnostic": 1},
    }

    audit = build_commit_readiness_audit(
        Path("D:/XinYu"),
        entries=entries,
        boundary_audit=PASSING_BOUNDARY,
        archive_delete_audit=archive,
    )

    assert audit["status"] == "needs_triage"
    assert audit["unknown_entry_count"] == 1
    assert audit["archive_delete"]["hold_count"] == 1
    assert len(audit["hold_reasons"]) == 2


def test_commit_readiness_holds_nonpassing_boundary() -> None:
    entries = parse_short_status(" M XinYu-Core/examples/agent-apps/xinyu/tests/test_new.py\n")
    boundary = {
        **PASSING_BOUNDARY,
        "status": "hold",
        "p0": {"generic_decision_count": 2},
    }

    audit = build_commit_readiness_audit(
        Path("D:/XinYu"),
        entries=entries,
        boundary_audit=boundary,
        archive_delete_audit=EMPTY_ARCHIVE,
    )

    assert audit["status"] == "needs_triage"
    assert audit["boundary_readiness"]["status"] == "hold"
    assert audit["hold_reasons"] == ["boundary readiness status is hold."]


def test_render_markdown_includes_closeout_and_privacy_note() -> None:
    audit = build_commit_readiness_audit(
        Path("D:/XinYu"),
        entries=parse_short_status(" M XinYu-Core/examples/agent-apps/xinyu/tests/test_new.py\n"),
        boundary_audit=PASSING_BOUNDARY,
        archive_delete_audit=EMPTY_ARCHIVE,
    )

    rendered = render_markdown(audit)

    assert "Commit Readiness Audit" in rendered
    assert "private memory bodies" in rendered
    assert "## Closeout Summary" in rendered
    assert "### kept" in rendered
    assert "### merged" in rendered
    assert "### archived" in rendered
    assert "### deleted" in rendered
    assert "git diff --check" in rendered
