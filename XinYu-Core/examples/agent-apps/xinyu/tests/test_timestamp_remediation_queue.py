from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from timestamp_remediation_queue import build_timestamp_remediation_queue  # noqa: E402


def test_remediation_queue_filters_to_actionable_classes_without_bodies() -> None:
    classifier = {
        "status": "hold",
        "classified_issue_count": 4,
        "items": [
            {
                "path": "cases/conversation/case.jsonl",
                "issue_class": "human_memory_missing_event_time",
                "zone": "cases",
                "file_type": "jsonl",
                "missing_count": 2,
                "invalid_count": 0,
                "body": "secret body should not appear",
            },
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/memory/context/recent_context.md",
                "issue_class": "invalid_timestamp_manual_review",
                "zone": "memory",
                "file_type": "md",
                "missing_count": 0,
                "invalid_count": 1,
            },
            {
                "path": "library/source.json",
                "issue_class": "metadata_timestamp_review",
                "zone": "library",
                "file_type": "json",
                "missing_count": 1,
                "invalid_count": 0,
            },
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/runtime/trace.jsonl",
                "issue_class": "operational_timestamp_not_human_memory",
                "zone": "runtime",
                "file_type": "jsonl",
                "missing_count": 10,
                "invalid_count": 0,
            },
        ],
    }

    queue = build_timestamp_remediation_queue(classifier)
    rendered = str(queue)

    assert queue["status"] == "ready_for_manual_review"
    assert queue["queue_count"] == 3
    assert queue["priority_counts"] == {"P0": 1, "P1": 1, "P2": 1}
    assert "operational_timestamp_not_human_memory" not in {item["issue_class"] for item in queue["items"]}
    assert "secret body" not in rendered

