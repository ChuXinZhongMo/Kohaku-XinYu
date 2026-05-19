from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from timestamp_dry_run_planner import build_timestamp_dry_run_plan, render_markdown  # noqa: E402


def test_dry_run_plan_uses_metadata_only_and_blocks_writes() -> None:
    queue = {
        "status": "ready_for_manual_review",
        "queue_count": 3,
        "items": [
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/memory/context/impulse_soup_trace.jsonl",
                "issue_class": "invalid_timestamp_manual_review",
                "priority": "P0",
                "zone": "memory",
                "file_type": "jsonl",
                "missing_count": 0,
                "invalid_count": 200,
                "body": "private body should not appear",
                "timestamp_value": "2026.5.18 22:37",
            },
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/memory/events/structured_events.jsonl",
                "issue_class": "human_memory_missing_event_time",
                "priority": "P1",
                "zone": "memory",
                "file_type": "jsonl",
                "missing_count": 5,
                "invalid_count": 0,
            },
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/data/conversation_experience/registry.json",
                "issue_class": "metadata_timestamp_review",
                "priority": "P2",
                "zone": "legacy.data",
                "file_type": "json",
                "missing_count": 1,
                "invalid_count": 0,
            },
        ],
    }

    plan = build_timestamp_dry_run_plan(queue)
    rendered = render_markdown(plan) + str(plan)

    assert plan["status"] == "dry_run_ready"
    assert plan["plan_item_count"] == 3
    assert all(item["write_allowed"] is False for item in plan["items"])
    assert plan["strategy_counts"]["manual_schema_review_before_any_edit"] == 1
    assert plan["strategy_counts"]["row_level_event_time_mapping_dry_run"] == 1
    assert plan["strategy_counts"]["confirm_metadata_role_or_exclude_from_human_memory_audit"] == 1
    assert "private body" not in rendered
    assert "2026.5.18 22:37" not in rendered


def test_dry_run_plan_selects_schema_aware_strategies() -> None:
    queue = {
        "items": [
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/memory/conversations.md",
                "issue_class": "human_memory_missing_event_time",
                "zone": "memory",
                "file_type": "md",
                "missing_count": 1,
            },
            {
                "path": (
                    "XinYu-Core/examples/agent-apps/xinyu/memory/creative/revisions/"
                    "before-platform/memory/creative/novel_state.md"
                ),
                "issue_class": "human_memory_missing_event_time",
                "zone": "memory",
                "file_type": "md",
                "missing_count": 1,
            },
            {
                "path": "XinYu-Core/examples/agent-apps/xinyu/memory/personality_change_state.json",
                "issue_class": "human_memory_missing_event_time",
                "zone": "memory",
                "file_type": "json",
                "missing_count": 1,
            },
        ],
    }

    plan_items = {item["path"]: item for item in build_timestamp_dry_run_plan(queue)["items"]}

    conversation = plan_items["XinYu-Core/examples/agent-apps/xinyu/memory/conversations.md"]
    assert conversation["schema_bucket"] == "dialogue_or_conversation_memory"
    assert conversation["proposed_strategy"] == "dialogue_archive_event_time_mapping_dry_run"
    assert conversation["required_evidence_source"] == "dialogue_archive_created_at_or_adapter_event_time"

    revision_path = (
        "XinYu-Core/examples/agent-apps/xinyu/memory/creative/revisions/"
        "before-platform/memory/creative/novel_state.md"
    )
    revision = plan_items[revision_path]
    assert revision["schema_bucket"] == "creative_revision_snapshot"
    assert revision["proposed_strategy"] == "snapshot_folder_time_as_candidate_only"
    assert revision["safety_status"] == "candidate_only_manual_confirmation_required"

    state = plan_items["XinYu-Core/examples/agent-apps/xinyu/memory/personality_change_state.json"]
    assert state["schema_bucket"] == "state_snapshot"
    assert state["proposed_strategy"] == "file_level_state_event_time_mapping_dry_run"
