from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from timestamp_invalid_schema_classifier import (  # noqa: E402
    classify_invalid_timestamp_schemas,
    render_markdown,
)


def test_invalid_schema_classifier_groups_p0_items_without_bodies_or_values() -> None:
    dry_run = {
        "status": "dry_run_ready",
        "plan_item_count": 3,
        "items": [
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/memory/context/impulse_soup_trace.jsonl",
                "priority": "P0",
                "zone": "memory",
                "file_type": "jsonl",
                "issue_class": "invalid_timestamp_manual_review",
                "schema_bucket": "append_only_event_log",
                "invalid_count": 200,
                "body": "secret body should not appear",
                "timestamp_value": "2026.5.18 22:37",
            },
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/memory/creative/planning/novel_state.md",
                "priority": "P0",
                "zone": "memory",
                "file_type": "md",
                "issue_class": "invalid_timestamp_manual_review",
                "schema_bucket": "creative_planning_doc",
                "invalid_count": 1,
            },
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/memory/context/recent_context.md",
                "priority": "P1",
                "zone": "memory",
                "file_type": "md",
                "issue_class": "human_memory_missing_event_time",
                "schema_bucket": "context_runtime_state",
                "invalid_count": 0,
            },
        ],
    }
    evidence = {
        "items": [
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/memory/context/impulse_soup_trace.jsonl",
                "writer_reference_count": 1,
                "manifest_reference_count": 1,
                "evidence_action": "writer_fix_candidate",
            }
        ]
    }

    result = classify_invalid_timestamp_schemas(dry_run, evidence_links=evidence)
    rendered = render_markdown(result) + str(result)

    assert result["status"] == "schema_review_ready"
    assert result["invalid_item_count"] == 2
    assert result["cause_counts"]["jsonl_row_timestamp_not_parseable"] == 1
    assert result["cause_counts"]["creative_markdown_frontmatter_timestamp_not_parseable"] == 1
    assert result["owner_counts"]["runtime_trace_manifest"] == 1
    assert result["items"][0]["write_allowed"] is False
    assert "secret body should not appear" not in rendered
    assert "2026.5.18 22:37" not in rendered


def test_invalid_schema_classifier_selects_safe_next_actions() -> None:
    dry_run = {
        "items": [
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/memory/context/qq_outbox_queue.json",
                "priority": "P0",
                "zone": "memory",
                "file_type": "json",
                "issue_class": "invalid_timestamp_manual_review",
                "schema_bucket": "context_runtime_state",
                "invalid_count": 1,
            },
            {
                "path": (
                    "XinYu-Core/examples/agent-apps/xinyu/memory/creative/revisions/"
                    "before-layout/memory/creative/novel_profile.md"
                ),
                "priority": "P0",
                "zone": "memory",
                "file_type": "md",
                "issue_class": "invalid_timestamp_manual_review",
                "schema_bucket": "creative_revision_snapshot",
                "invalid_count": 1,
            },
        ]
    }
    evidence = {
        "items": [
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/memory/context/qq_outbox_queue.json",
                "writer_reference_count": 0,
                "manifest_reference_count": 1,
                "evidence_action": "manual_data_review_required",
            }
        ]
    }

    items = classify_invalid_timestamp_schemas(dry_run, evidence_links=evidence)["items"]
    by_path = {item["path"]: item for item in items}

    queue = by_path["XinYu-Core/examples/agent-apps/xinyu/memory/context/qq_outbox_queue.json"]
    assert queue["schema_owner"] == "queue_boundary_manifest"
    assert queue["next_action"] == "inspect_manifest_owner_schema"

    revision = by_path[
        "XinYu-Core/examples/agent-apps/xinyu/memory/creative/revisions/"
        "before-layout/memory/creative/novel_profile.md"
    ]
    assert revision["schema_owner"] == "creative_revision_snapshot_owner"
    assert revision["next_action"] == "manual_snapshot_policy_review"
