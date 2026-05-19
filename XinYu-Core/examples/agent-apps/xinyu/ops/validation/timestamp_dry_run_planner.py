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
DEFAULT_QUEUE_JSON = PROJECT_ROOT / "worklog/xinyu-timestamp-remediation-queue-2026-05-18.json"

PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2}


def build_timestamp_dry_run_plan(queue: dict[str, Any]) -> dict[str, Any]:
    raw_items = [item for item in queue.get("items") or [] if isinstance(item, dict)]
    items = sorted((normalize_plan_item(item) for item in raw_items), key=plan_sort_key)
    strategy_counts = Counter(item["proposed_strategy"] for item in items)
    safety_counts = Counter(item["safety_status"] for item in items)
    evidence_counts = Counter(item["required_evidence_source"] for item in items)
    bucket_counts = Counter(item["schema_bucket"] for item in items)
    return {
        "status": "dry_run_ready" if items else "empty",
        "source_status": str(queue.get("status", "")),
        "source_queue_count": int(queue.get("queue_count") or len(raw_items)),
        "plan_item_count": len(items),
        "strategy_counts": dict(sorted(strategy_counts.items())),
        "safety_counts": dict(sorted(safety_counts.items())),
        "evidence_counts": dict(sorted(evidence_counts.items())),
        "schema_bucket_counts": dict(sorted(bucket_counts.items())),
        "items": items,
        "privacy_note": (
            "Dry-run remediation plan uses queue metadata only: path, issue class, priority, zone, "
            "file type, and counts. It does not read or print memory bodies, JSON/JSONL bodies, "
            "raw QQ payloads, tokens, timestamp values, or secrets. No writes are authorized."
        ),
    }


def normalize_plan_item(item: dict[str, Any]) -> dict[str, Any]:
    issue_class = str(item.get("issue_class", ""))
    path = str(item.get("path", ""))
    zone = str(item.get("zone", ""))
    file_type = str(item.get("file_type", ""))
    bucket = schema_bucket(path=path, zone=zone, file_type=file_type)
    return {
        "priority": str(item.get("priority") or priority_for_issue_class(issue_class)),
        "path": path,
        "issue_class": issue_class,
        "zone": zone,
        "file_type": file_type,
        "missing_count": int(item.get("missing_count") or 0),
        "invalid_count": int(item.get("invalid_count") or 0),
        "schema_bucket": bucket,
        "proposed_strategy": proposed_strategy(issue_class=issue_class, bucket=bucket, file_type=file_type),
        "required_evidence_source": required_evidence_source(
            issue_class=issue_class, bucket=bucket, file_type=file_type
        ),
        "safety_status": safety_status(issue_class=issue_class, bucket=bucket, file_type=file_type),
        "write_allowed": False,
    }


def priority_for_issue_class(issue_class: str) -> str:
    if issue_class == "invalid_timestamp_manual_review":
        return "P0"
    if issue_class == "human_memory_missing_event_time":
        return "P1"
    return "P2"


def schema_bucket(*, path: str, zone: str, file_type: str) -> str:
    normalized = path.replace("\\", "/").lower()
    name = normalized.rsplit("/", 1)[-1]
    if "/data/conversation_experience/" in normalized:
        return "legacy_conversation_case"
    if "/memory/creative/revisions/" in normalized:
        return "creative_revision_snapshot"
    if "/memory/creative/planning/" in normalized:
        return "creative_planning_doc"
    if "/memory/events/" in normalized or name.endswith("_events.jsonl") or name.endswith("_trace.jsonl"):
        return "append_only_event_log"
    if "/memory/context/" in normalized:
        return "context_runtime_state"
    if "/memory/archive/" in normalized:
        return "archive_state"
    if any(marker in name for marker in ("conversation", "dialogue", "recent_context")):
        return "dialogue_or_conversation_memory"
    if file_type == "jsonl":
        return "append_only_event_log"
    if name.endswith("_state.md") or name.endswith("_state.json") or "state" in name:
        return "state_snapshot"
    if any(marker in name for marker in ("policy", "index", "manifest", "registry", "readme")):
        return "policy_or_index_doc"
    if zone == "legacy.data":
        return "legacy_metadata"
    if zone == "memory":
        return "memory_note"
    return "unknown_metadata"


def proposed_strategy(*, issue_class: str, bucket: str, file_type: str) -> str:
    if issue_class == "invalid_timestamp_manual_review":
        return "manual_schema_review_before_any_edit"
    if issue_class == "metadata_timestamp_review":
        return "confirm_metadata_role_or_exclude_from_human_memory_audit"
    if issue_class != "human_memory_missing_event_time":
        return "manual_review_before_any_edit"
    if file_type == "jsonl" or bucket == "append_only_event_log":
        return "row_level_event_time_mapping_dry_run"
    if bucket == "creative_revision_snapshot":
        return "snapshot_folder_time_as_candidate_only"
    if bucket == "dialogue_or_conversation_memory":
        return "dialogue_archive_event_time_mapping_dry_run"
    if bucket in {"state_snapshot", "archive_state", "context_runtime_state"}:
        return "file_level_state_event_time_mapping_dry_run"
    if file_type == "json":
        return "file_or_record_level_metadata_mapping_dry_run"
    return "file_level_frontmatter_event_time_mapping_dry_run"


def required_evidence_source(*, issue_class: str, bucket: str, file_type: str) -> str:
    if issue_class == "invalid_timestamp_manual_review":
        return "schema_owner_plus_original_emission_code"
    if issue_class == "metadata_timestamp_review":
        return "audit_policy_owner_and_schema_exclusion_rule"
    if issue_class != "human_memory_missing_event_time":
        return "manual_schema_owner_decision"
    if file_type == "jsonl" or bucket == "append_only_event_log":
        return "per_row_event_source_or_archive_index"
    if bucket == "creative_revision_snapshot":
        return "snapshot_directory_provenance_plus_revision_manifest"
    if bucket == "dialogue_or_conversation_memory":
        return "dialogue_archive_created_at_or_adapter_event_time"
    if bucket in {"state_snapshot", "archive_state", "context_runtime_state"}:
        return "owning_writer_received_at_or_state_update_event"
    if file_type == "json":
        return "json_schema_owner_or_source_adapter_event_time"
    return "file_level_frontmatter_or_authoring_event_record"


def safety_status(*, issue_class: str, bucket: str, file_type: str) -> str:
    if issue_class == "invalid_timestamp_manual_review":
        return "blocked_until_invalid_values_are_manually_classified"
    if issue_class == "metadata_timestamp_review":
        return "review_only_may_be_excluded"
    if issue_class != "human_memory_missing_event_time":
        return "blocked_until_manual_decision"
    if file_type == "jsonl" or bucket == "append_only_event_log":
        return "blocked_until_row_schema_verified"
    if bucket == "creative_revision_snapshot":
        return "candidate_only_manual_confirmation_required"
    return "dry_run_only_manual_confirmation_required"


def plan_sort_key(item: dict[str, Any]) -> tuple[int, str, str]:
    return (
        PRIORITY_RANK.get(str(item.get("priority", "")), 99),
        str(item.get("schema_bucket", "")),
        str(item.get("path", "")),
    )


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# XinYu Timestamp Dry-Run Remediation Plan",
        "",
        plan["privacy_note"],
        "",
        f"- status: {plan['status']}",
        f"- source_status: {plan['source_status']}",
        f"- source_queue_count: {plan['source_queue_count']}",
        f"- plan_item_count: {plan['plan_item_count']}",
        "",
        "## Strategy Counts",
        "",
    ]
    append_counts(lines, plan.get("strategy_counts") or {})
    lines.extend(["", "## Safety Counts", ""])
    append_counts(lines, plan.get("safety_counts") or {})
    lines.extend(["", "## Schema Bucket Counts", ""])
    append_counts(lines, plan.get("schema_bucket_counts") or {})
    lines.extend(["", "## Plan Items", ""])
    items = plan.get("items") or []
    if not items:
        lines.append("- none")
    else:
        for item in items:
            lines.append(
                f"- `{item['path']}` | priority={item['priority']} | class={item['issue_class']} | "
                f"bucket={item['schema_bucket']} | strategy={item['proposed_strategy']} | "
                f"evidence={item['required_evidence_source']} | safety={item['safety_status']} | "
                f"missing={item['missing_count']} | invalid={item['invalid_count']} | write_allowed=false"
            )
    return "\n".join(lines).rstrip() + "\n"


def append_counts(lines: list[str], counts: dict[str, int]) -> None:
    if not counts:
        lines.append("- none")
        return
    for name, count in counts.items():
        lines.append(f"- {name}: {count}")


def load_queue(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {"status": "missing_or_invalid_queue", "items": []}
    return data if isinstance(data, dict) else {"status": "invalid_queue_shape", "items": []}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a metadata-only timestamp remediation dry-run plan.")
    parser.add_argument("--queue-json", type=Path, default=DEFAULT_QUEUE_JSON)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    plan = build_timestamp_dry_run_plan(load_queue(args.queue_json))
    output = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) if args.json else render_markdown(plan)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
