from __future__ import annotations

import json
import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from timestamp_evidence_linker import build_timestamp_evidence_links, render_markdown  # noqa: E402


APP_PREFIX = "XinYu-Core/examples/agent-apps/xinyu"


def test_evidence_linker_maps_source_manifest_and_exclusion_without_bodies(tmp_path: Path) -> None:
    app = tmp_path / APP_PREFIX
    source = app / "xinyu_event_writer.py"
    manifest = app / "stores/queue_boundary_manifest.json"
    memory = app / "memory/events/structured_events.jsonl"
    source.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    memory.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        'EVENT_PATH = "memory/events/structured_events.jsonl"\nPath(EVENT_PATH).write_text("{}\\n")\n',
        encoding="utf-8",
    )
    memory.write_text('{"body": "private body should not appear"}\n', encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "manifest_id": "stores/queue_boundary_manifest",
                "queues": [{"path": "memory/context/qq_outbox_queue.json"}],
            }
        ),
        encoding="utf-8",
    )
    dry_run = {
        "status": "dry_run_ready",
        "plan_item_count": 3,
        "items": [
            {
                "path": f"{APP_PREFIX}/memory/events/structured_events.jsonl",
                "issue_class": "human_memory_missing_event_time",
                "priority": "P1",
                "zone": "memory",
                "schema_bucket": "append_only_event_log",
                "proposed_strategy": "row_level_event_time_mapping_dry_run",
                "body": "secret body should not appear",
                "timestamp_value": "2026.5.18 22:37",
            },
            {
                "path": f"{APP_PREFIX}/memory/context/qq_outbox_queue.json",
                "issue_class": "invalid_timestamp_manual_review",
                "priority": "P0",
                "zone": "memory",
                "schema_bucket": "context_runtime_state",
                "proposed_strategy": "manual_schema_review_before_any_edit",
            },
            {
                "path": f"{APP_PREFIX}/data/external/wildchat-rows.json",
                "issue_class": "metadata_timestamp_review",
                "priority": "P2",
                "zone": "legacy.data",
                "schema_bucket": "legacy_metadata",
                "proposed_strategy": "confirm_metadata_role_or_exclude_from_human_memory_audit",
            },
        ],
    }

    result = build_timestamp_evidence_links(dry_run, repo_root=tmp_path, app_root=app)
    by_path = {item["path"]: item for item in result["items"]}
    rendered = render_markdown(result) + str(result)

    event_item = by_path[f"{APP_PREFIX}/memory/events/structured_events.jsonl"]
    assert event_item["evidence_action"] == "writer_fix_candidate"
    assert event_item["writer_reference_examples"] == ["xinyu_event_writer.py"]
    assert event_item["source_reference_examples"] == ["xinyu_event_writer.py"]
    assert event_item["write_allowed"] is False

    queue_item = by_path[f"{APP_PREFIX}/memory/context/qq_outbox_queue.json"]
    assert queue_item["evidence_action"] == "manual_data_review_required"
    assert queue_item["manifest_reference_examples"] == ["stores/queue_boundary_manifest"]

    legacy_item = by_path[f"{APP_PREFIX}/data/external/wildchat-rows.json"]
    assert legacy_item["evidence_action"] == "auto_exclude_policy_candidate"
    assert legacy_item["evidence_status"] == "policy_candidate_without_body_review"

    assert "private body should not appear" not in rendered
    assert "secret body should not appear" not in rendered
    assert "2026.5.18 22:37" not in rendered


def test_evidence_linker_keeps_items_blocked_when_no_evidence_exists(tmp_path: Path) -> None:
    app = tmp_path / APP_PREFIX
    app.mkdir(parents=True)
    dry_run = {
        "items": [
            {
                "path": f"{APP_PREFIX}/memory/general.md",
                "issue_class": "human_memory_missing_event_time",
                "priority": "P1",
                "zone": "memory",
                "schema_bucket": "memory_note",
                "proposed_strategy": "file_level_frontmatter_event_time_mapping_dry_run",
            }
        ]
    }

    result = build_timestamp_evidence_links(dry_run, repo_root=tmp_path, app_root=app)

    assert result["items"][0]["evidence_action"] == "blocked_no_evidence"
    assert result["items"][0]["evidence_status"] == "no_evidence_found"
    assert result["items"][0]["write_allowed"] is False


def test_evidence_linker_does_not_treat_config_or_manifest_as_writers(tmp_path: Path) -> None:
    app = tmp_path / APP_PREFIX
    app.mkdir(parents=True)
    config = app / "config.yaml"
    manifest = app / "custom/inner_framework_manifest.py"
    config.write_text('path: "memory/context/example_state.json"\n', encoding="utf-8")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text('PATH = "memory/context/example_state.json"\n', encoding="utf-8")
    dry_run = {
        "items": [
            {
                "path": f"{APP_PREFIX}/memory/context/example_state.json",
                "issue_class": "human_memory_missing_event_time",
                "priority": "P1",
                "zone": "memory",
                "schema_bucket": "context_runtime_state",
                "proposed_strategy": "file_level_state_event_time_mapping_dry_run",
            }
        ]
    }

    result = build_timestamp_evidence_links(dry_run, repo_root=tmp_path, app_root=app)
    item = result["items"][0]

    assert item["evidence_action"] == "blocked_no_evidence"
    assert item["writer_reference_count"] == 0
    assert item["source_reference_count"] == 0
