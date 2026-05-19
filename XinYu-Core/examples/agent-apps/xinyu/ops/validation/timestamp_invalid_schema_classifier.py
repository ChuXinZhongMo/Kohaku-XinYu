from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from ._validation_paths import ensure_validation_paths
except ImportError:  # pragma: no cover - direct script execution
    from _validation_paths import ensure_validation_paths


APP_ROOT = ensure_validation_paths("ops/validation")
PROJECT_ROOT = APP_ROOT.parents[3]
DEFAULT_DRY_RUN_JSON = PROJECT_ROOT / "worklog/xinyu-timestamp-dry-run-plan-post-p12-2026-05-19.json"
DEFAULT_EVIDENCE_JSON = PROJECT_ROOT / "worklog/xinyu-timestamp-evidence-linker-post-p12-2026-05-19.json"


def classify_invalid_timestamp_schemas(
    dry_run_plan: dict[str, Any],
    *,
    evidence_links: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence_by_path = {
        str(item.get("path", "")): item
        for item in (evidence_links or {}).get("items", [])
        if isinstance(item, dict)
    }
    invalid_items = [
        item
        for item in dry_run_plan.get("items") or []
        if isinstance(item, dict) and str(item.get("issue_class")) == "invalid_timestamp_manual_review"
    ]
    classified = [classify_invalid_item(item, evidence_by_path=evidence_by_path) for item in invalid_items]
    cause_counts = Counter(item["likely_invalid_cause"] for item in classified)
    owner_counts = Counter(item["schema_owner"] for item in classified)
    action_counts = Counter(item["next_action"] for item in classified)
    bucket_counts = Counter(item["schema_bucket"] for item in classified)
    return {
        "status": "schema_review_ready" if classified else "empty",
        "source_status": str(dry_run_plan.get("status", "")),
        "source_plan_item_count": int(dry_run_plan.get("plan_item_count") or len(dry_run_plan.get("items") or [])),
        "invalid_item_count": len(classified),
        "cause_counts": dict(sorted(cause_counts.items())),
        "owner_counts": dict(sorted(owner_counts.items())),
        "action_counts": dict(sorted(action_counts.items())),
        "schema_bucket_counts": dict(sorted(bucket_counts.items())),
        "items": classified,
        "privacy_note": (
            "Invalid timestamp schema classifier uses dry-run and evidence-link metadata only: paths, "
            "schema buckets, file types, counts, and source/manifest reference counts. It does not read "
            "or print memory bodies, JSON/JSONL bodies, raw QQ payloads, tokens, timestamp values, or secrets."
        ),
    }


def classify_invalid_item(item: dict[str, Any], *, evidence_by_path: dict[str, dict[str, Any]]) -> dict[str, Any]:
    path = str(item.get("path", ""))
    file_type = str(item.get("file_type", ""))
    bucket = str(item.get("schema_bucket", ""))
    evidence = evidence_by_path.get(path, {})
    writer_count = int(evidence.get("writer_reference_count") or 0)
    manifest_count = int(evidence.get("manifest_reference_count") or 0)
    owner = schema_owner(path=path, bucket=bucket)
    cause = likely_invalid_cause(path=path, file_type=file_type, bucket=bucket)
    next_action = next_action_for(
        cause=cause,
        bucket=bucket,
        writer_count=writer_count,
        manifest_count=manifest_count,
    )
    return {
        "priority": str(item.get("priority", "P0")),
        "path": path,
        "zone": str(item.get("zone", "")),
        "file_type": file_type,
        "invalid_count": int(item.get("invalid_count") or 0),
        "schema_bucket": bucket,
        "likely_invalid_cause": cause,
        "schema_owner": owner,
        "owner_boundary": owner_boundary(owner),
        "writer_reference_count": writer_count,
        "manifest_reference_count": manifest_count,
        "evidence_action": str(evidence.get("evidence_action", "unknown")),
        "next_action": next_action,
        "safety_status": "blocked_until_schema_owner_review",
        "write_allowed": False,
    }


def likely_invalid_cause(*, path: str, file_type: str, bucket: str) -> str:
    normalized = path.replace("\\", "/").lower()
    if file_type == "jsonl":
        return "jsonl_row_timestamp_not_parseable"
    if file_type == "json":
        return "json_field_timestamp_not_parseable"
    if bucket == "creative_revision_snapshot":
        return "snapshot_markdown_frontmatter_timestamp_not_parseable"
    if bucket == "creative_planning_doc":
        return "creative_markdown_frontmatter_timestamp_not_parseable"
    if bucket == "context_runtime_state":
        return "context_state_frontmatter_timestamp_not_parseable"
    if bucket == "archive_state":
        return "archive_state_frontmatter_timestamp_not_parseable"
    if bucket == "state_snapshot":
        return "state_snapshot_frontmatter_timestamp_not_parseable"
    if bucket == "policy_or_index_doc":
        return "policy_or_index_frontmatter_timestamp_not_parseable"
    if bucket == "append_only_event_log":
        return "event_log_state_frontmatter_timestamp_not_parseable"
    if bucket == "legacy_conversation_case" or "/data/conversation_experience/" in normalized:
        return "legacy_case_timestamp_not_parseable"
    return "memory_note_frontmatter_timestamp_not_parseable"


def schema_owner(*, path: str, bucket: str) -> str:
    normalized = path.replace("\\", "/").lower()
    if "impulse_soup_trace.jsonl" in normalized:
        return "runtime_trace_manifest"
    if "qq_outbox_queue.json" in normalized:
        return "queue_boundary_manifest"
    if "/data/conversation_experience/" in normalized:
        return "conversation_experience_dataset_importer"
    if bucket == "creative_revision_snapshot":
        return "creative_revision_snapshot_owner"
    if bucket == "creative_planning_doc":
        return "creative_writing_pipeline"
    if bucket == "context_runtime_state":
        return "runtime_context_state_writers"
    if bucket == "archive_state":
        return "archive_pipeline"
    if bucket == "state_snapshot":
        return "state_snapshot_writers"
    if bucket == "policy_or_index_doc":
        return "manual_policy_doc_owner"
    if bucket == "append_only_event_log":
        return "event_log_boundary_owner"
    if bucket == "legacy_conversation_case":
        return "conversation_experience_dataset_importer"
    return "memory_note_writers"


def owner_boundary(owner: str) -> str:
    boundaries = {
        "archive_pipeline": "custom/archive_*_engine.py",
        "conversation_experience_dataset_importer": "data/conversation_experience import boundary",
        "creative_revision_snapshot_owner": "memory/creative/revisions",
        "creative_writing_pipeline": "memory/creative/planning",
        "event_log_boundary_owner": "stores/event_boundary_manifest",
        "manual_policy_doc_owner": "manual markdown policy owner",
        "memory_note_writers": "memory note writer or manual authoring path",
        "queue_boundary_manifest": "stores/queue_boundary_manifest",
        "runtime_context_state_writers": "memory/context state writers",
        "runtime_trace_manifest": "stores/runtime_trace_manifest",
        "state_snapshot_writers": "state snapshot writer modules",
    }
    return boundaries.get(owner, "manual schema owner review")


def next_action_for(*, cause: str, bucket: str, writer_count: int, manifest_count: int) -> str:
    if writer_count > 0:
        return "inspect_writer_future_timestamp_format"
    if manifest_count > 0:
        return "inspect_manifest_owner_schema"
    if bucket == "creative_revision_snapshot":
        return "manual_snapshot_policy_review"
    if cause.startswith("legacy_case_"):
        return "dataset_import_policy_review"
    if cause.startswith("jsonl_"):
        return "manual_row_schema_review"
    return "manual_frontmatter_schema_review"


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# XinYu Invalid Timestamp Schema Classifier",
        "",
        result["privacy_note"],
        "",
        f"- status: {result['status']}",
        f"- source_status: {result['source_status']}",
        f"- source_plan_item_count: {result['source_plan_item_count']}",
        f"- invalid_item_count: {result['invalid_item_count']}",
        "",
        "## Cause Counts",
        "",
    ]
    append_counts(lines, result.get("cause_counts") or {})
    lines.extend(["", "## Owner Counts", ""])
    append_counts(lines, result.get("owner_counts") or {})
    lines.extend(["", "## Action Counts", ""])
    append_counts(lines, result.get("action_counts") or {})
    lines.extend(["", "## Items", ""])
    items = result.get("items") or []
    if not items:
        lines.append("- none")
    else:
        for item in items:
            lines.append(
                f"- `{item['path']}` | bucket={item['schema_bucket']} | cause={item['likely_invalid_cause']} | "
                f"owner={item['schema_owner']} | action={item['next_action']} | writers={item['writer_reference_count']} | "
                f"manifests={item['manifest_reference_count']} | invalid={item['invalid_count']} | write_allowed=false"
            )
    return "\n".join(lines).rstrip() + "\n"


def append_counts(lines: list[str], counts: dict[str, int]) -> None:
    if not counts:
        lines.append("- none")
        return
    for name, count in counts.items():
        lines.append(f"- {name}: {count}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {"status": "missing_or_invalid_json", "items": []}
    return data if isinstance(data, dict) else {"status": "invalid_json_shape", "items": []}


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify invalid timestamp schemas without reading private bodies.")
    parser.add_argument("--dry-run-json", type=Path, default=DEFAULT_DRY_RUN_JSON)
    parser.add_argument("--evidence-json", type=Path, default=DEFAULT_EVIDENCE_JSON)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = classify_invalid_timestamp_schemas(
        load_json(args.dry_run_json),
        evidence_links=load_json(args.evidence_json),
    )
    output = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if args.json else render_markdown(result)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
