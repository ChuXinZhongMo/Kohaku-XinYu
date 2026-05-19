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
DEFAULT_CLASSIFIER_JSON = PROJECT_ROOT / "worklog/xinyu-timestamp-issue-classifier-2026-05-18.json"
ACTIONABLE_CLASSES = {
    "human_memory_missing_event_time",
    "invalid_timestamp_manual_review",
    "metadata_timestamp_review",
}


def build_timestamp_remediation_queue(classifier: dict[str, Any]) -> dict[str, Any]:
    items = [item for item in classifier.get("items") or [] if isinstance(item, dict)]
    actionable = [normalize_queue_item(item) for item in items if str(item.get("issue_class")) in ACTIONABLE_CLASSES]
    class_counts = Counter(item["issue_class"] for item in actionable)
    priority_counts = Counter(item["priority"] for item in actionable)
    return {
        "status": "ready_for_manual_review" if actionable else "empty",
        "source_status": classifier.get("status", ""),
        "source_classified_issue_count": classifier.get("classified_issue_count", 0),
        "queue_count": len(actionable),
        "class_counts": dict(sorted(class_counts.items())),
        "priority_counts": dict(sorted(priority_counts.items())),
        "items": actionable,
        "privacy_note": (
            "Timestamp remediation queue contains paths, classes, priorities, and counts only. "
            "It does not include memory bodies, JSON/JSONL bodies, raw QQ payloads, tokens, or timestamp values."
        ),
    }


def normalize_queue_item(item: dict[str, Any]) -> dict[str, Any]:
    issue_class = str(item.get("issue_class", ""))
    return {
        "priority": priority_for_class(issue_class),
        "path": str(item.get("path", "")),
        "issue_class": issue_class,
        "zone": str(item.get("zone", "")),
        "file_type": str(item.get("file_type", "")),
        "missing_count": int(item.get("missing_count") or 0),
        "invalid_count": int(item.get("invalid_count") or 0),
        "recommended_action": recommended_action(issue_class),
    }


def priority_for_class(issue_class: str) -> str:
    if issue_class == "invalid_timestamp_manual_review":
        return "P0"
    if issue_class == "human_memory_missing_event_time":
        return "P1"
    return "P2"


def recommended_action(issue_class: str) -> str:
    if issue_class == "invalid_timestamp_manual_review":
        return "manual_schema_review_before_any_edit"
    if issue_class == "human_memory_missing_event_time":
        return "review_for_safe_event_time_backfill"
    return "confirm_metadata_role_or_exclude"


def render_markdown(queue: dict[str, Any]) -> str:
    lines = [
        "# XinYu Timestamp Remediation Queue",
        "",
        queue["privacy_note"],
        "",
        f"- status: {queue['status']}",
        f"- source_status: {queue['source_status']}",
        f"- source_classified_issue_count: {queue['source_classified_issue_count']}",
        f"- queue_count: {queue['queue_count']}",
        "",
        "## Class Counts",
        "",
    ]
    for issue_class, count in (queue.get("class_counts") or {}).items():
        lines.append(f"- {issue_class}: {count}")
    if not queue.get("class_counts"):
        lines.append("- none")
    lines.extend(["", "## Priority Counts", ""])
    for priority, count in (queue.get("priority_counts") or {}).items():
        lines.append(f"- {priority}: {count}")
    if not queue.get("priority_counts"):
        lines.append("- none")
    lines.extend(["", "## Queue Items", ""])
    items = queue.get("items") or []
    if not items:
        lines.append("- none")
    else:
        for item in items:
            lines.append(
                f"- `{item['path']}` | priority={item['priority']} | class={item['issue_class']} | "
                f"action={item['recommended_action']} | missing={item['missing_count']} | invalid={item['invalid_count']}"
            )
    return "\n".join(lines).rstrip() + "\n"


def load_classifier(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {"status": "missing_or_invalid_classifier", "items": []}
    return data if isinstance(data, dict) else {"status": "invalid_classifier_shape", "items": []}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a non-destructive timestamp remediation queue.")
    parser.add_argument("--classifier-json", type=Path, default=DEFAULT_CLASSIFIER_JSON)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    queue = build_timestamp_remediation_queue(load_classifier(args.classifier_json))
    output = json.dumps(queue, ensure_ascii=False, indent=2, sort_keys=True) if args.json else render_markdown(queue)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
