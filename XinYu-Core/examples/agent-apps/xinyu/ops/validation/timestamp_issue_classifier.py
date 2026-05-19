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
DEFAULT_AUDIT_JSON = PROJECT_ROOT / "worklog/xinyu-timestamp-provenance-audit-2026-05-18.json"


def classify_timestamp_issues(audit: dict[str, Any], *, item_limit: int = 200) -> dict[str, Any]:
    issues = [item for item in audit.get("issues") or [] if isinstance(item, dict)]
    classified = []
    for item in issues:
        issue_class = classify_issue(item)
        classified.append(
            {
                "path": str(item.get("path", "")),
                "zone": str(item.get("zone", "")),
                "file_type": str(item.get("file_type", "")),
                "missing_count": int(item.get("missing_count") or 0),
                "invalid_count": int(item.get("invalid_count") or 0),
                "issue_class": issue_class,
            }
        )
    class_counts = Counter(item["issue_class"] for item in classified)
    return {
        "status": "hold" if classified else "pass",
        "source_status": audit.get("status", ""),
        "source_total_files": audit.get("total_files", 0),
        "classified_issue_count": len(classified),
        "class_counts": dict(sorted(class_counts.items())),
        "item_limit": max(0, int(item_limit)),
        "items": classified[: max(0, int(item_limit))],
        "privacy_note": (
            "Classifies P06 metadata-only issue records by path, zone, file type, and counts only. "
            "Does not read or print memory bodies, JSON/JSONL bodies, raw QQ payloads, tokens, or timestamp values."
        ),
    }


def classify_issue(item: dict[str, Any]) -> str:
    path = str(item.get("path", "")).replace("\\", "/").lower()
    zone = str(item.get("zone", "")).lower()
    missing = int(item.get("missing_count") or 0)
    invalid = int(item.get("invalid_count") or 0)

    if zone == "runtime" or "/runtime/" in path:
        return "operational_timestamp_not_human_memory"
    if any(marker in path for marker in ("/__pycache__/", "/pytest-tmp/", "/pytest_tmp/")):
        return "safe_generated_artifact_no_backfill_needed"
    if path.endswith(("readme.md", "index.md")) and missing and not invalid:
        return "safe_index_or_docs_no_backfill_needed"
    if zone == "legacy.data" and "/data/external/" in path and missing and not invalid:
        return "safe_legacy_external_dataset_no_backfill_needed"
    if "/memory/context/" in path and path.endswith("_state.md"):
        return "operational_timestamp_not_human_memory"
    if invalid:
        return "invalid_timestamp_manual_review"
    if zone in {"memory", "cases", "library"} and missing:
        return "human_memory_missing_event_time"
    if missing:
        return "metadata_timestamp_review"
    return "timestamp_issue_review"


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# XinYu Timestamp Issue Classifier",
        "",
        result["privacy_note"],
        "",
        f"- status: {result['status']}",
        f"- source_status: {result['source_status']}",
        f"- source_total_files: {result['source_total_files']}",
        f"- classified_issue_count: {result['classified_issue_count']}",
        "",
        "## Class Counts",
        "",
    ]
    class_counts = result.get("class_counts") or {}
    if class_counts:
        for issue_class, count in class_counts.items():
            lines.append(f"- {issue_class}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Review Items", ""])
    items = result.get("items") or []
    if not items:
        lines.append("- none")
    else:
        for item in items:
            lines.append(
                f"- `{item['path']}` | class={item['issue_class']} | zone={item['zone']} | "
                f"type={item['file_type']} | missing={item['missing_count']} | invalid={item['invalid_count']}"
            )
    return "\n".join(lines).rstrip() + "\n"


def load_audit(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {"status": "missing_or_invalid_audit", "issues": []}
    return data if isinstance(data, dict) else {"status": "invalid_audit_shape", "issues": []}


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify timestamp audit issues without reading private bodies.")
    parser.add_argument("--audit-json", type=Path, default=DEFAULT_AUDIT_JSON)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--item-limit", type=int, default=200)
    args = parser.parse_args()

    result = classify_timestamp_issues(load_audit(args.audit_json), item_limit=args.item_limit)
    output = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if args.json else render_markdown(result)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
