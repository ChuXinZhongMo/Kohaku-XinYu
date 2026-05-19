from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from timestamp_issue_classifier import classify_issue, classify_timestamp_issues  # noqa: E402


def test_classify_issue_separates_operational_docs_and_human_memory() -> None:
    assert (
        classify_issue(
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/runtime/events/a.jsonl",
                "zone": "runtime",
                "missing_count": 10,
                "invalid_count": 0,
            }
        )
        == "operational_timestamp_not_human_memory"
    )
    assert (
        classify_issue(
            {
                "path": "library/README.md",
                "zone": "library",
                "missing_count": 1,
                "invalid_count": 0,
            }
        )
        == "safe_index_or_docs_no_backfill_needed"
    )
    assert (
        classify_issue(
            {
                "path": "cases/conversation/case.jsonl",
                "zone": "cases",
                "missing_count": 1,
                "invalid_count": 0,
            }
        )
        == "human_memory_missing_event_time"
    )
    assert (
        classify_issue(
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/data/external/wildchat-rows.json",
                "zone": "legacy.data",
                "missing_count": 1,
                "invalid_count": 0,
            }
        )
        == "safe_legacy_external_dataset_no_backfill_needed"
    )
    assert (
        classify_issue(
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/memory/context/recent_context.md",
                "zone": "memory",
                "missing_count": 0,
                "invalid_count": 1,
            }
        )
        == "invalid_timestamp_manual_review"
    )


def test_classifier_uses_audit_metadata_without_body_or_values() -> None:
    audit = {
        "status": "hold",
        "total_files": 3,
        "issues": [
            {
                "path": "cases/conversation/case.jsonl",
                "zone": "cases",
                "file_type": "jsonl",
                "missing_count": 1,
                "invalid_count": 0,
                "secret": "private body should not appear",
            },
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/runtime/trace.jsonl",
                "zone": "runtime",
                "file_type": "jsonl",
                "missing_count": 4,
                "invalid_count": 0,
            },
        ],
    }

    result = classify_timestamp_issues(audit)
    rendered = str(result)

    assert result["status"] == "hold"
    assert result["class_counts"]["human_memory_missing_event_time"] == 1
    assert result["class_counts"]["operational_timestamp_not_human_memory"] == 1
    assert "private body" not in rendered
