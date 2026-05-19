from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

try:
    from ._validation_paths import ensure_validation_paths
except ImportError:  # pragma: no cover - direct script execution
    from _validation_paths import ensure_validation_paths


APP_ROOT = ensure_validation_paths("ops/validation")
PROJECT_ROOT = APP_ROOT.parents[3]
APP_REL = Path("XinYu-Core/examples/agent-apps/xinyu")
DEFAULT_DRY_RUN_JSON = PROJECT_ROOT / "worklog/xinyu-timestamp-dry-run-plan-2026-05-19.json"

SOURCE_SUFFIXES = {".py", ".ps1", ".ts", ".tsx", ".js"}
WRITER_TOKENS = (
    ".append(",
    ".open(",
    ".write(",
    "append_jsonl",
    "enqueue_",
    "json.dump",
    "open(",
    "persist",
    "record_",
    "save_",
    "write_text(",
)
SKIP_SOURCE_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "memory",
    "runtime",
    "stores",
    "tests",
    "ops",
    "logs",
    "project-plans",
    "node_modules",
    "dist",
    "build",
}
MAX_SOURCE_FILE_BYTES = 1_000_000


def build_timestamp_evidence_links(
    dry_run_plan: dict[str, Any],
    *,
    repo_root: Path = PROJECT_ROOT,
    app_root: Path = APP_ROOT,
    max_examples: int = 6,
) -> dict[str, Any]:
    raw_items = [item for item in dry_run_plan.get("items") or [] if isinstance(item, dict)]
    manifest_index = build_manifest_path_index(app_root)
    reference_index = build_source_reference_index(app_root, [str(item.get("path", "")) for item in raw_items])
    items = [
        link_plan_item(
            item,
            manifest_index=manifest_index,
            source_index=reference_index["source"],
            writer_index=reference_index["writer"],
            max_examples=max_examples,
        )
        for item in raw_items
    ]
    action_counts = Counter(item["evidence_action"] for item in items)
    status_counts = Counter(item["evidence_status"] for item in items)
    manifest_counts = Counter(item["manifest_status"] for item in items)
    source_counts = Counter(item["source_status"] for item in items)
    writer_counts = Counter(item["writer_status"] for item in items)
    return {
        "status": "evidence_linked" if items else "empty",
        "source_status": str(dry_run_plan.get("status", "")),
        "source_plan_item_count": int(dry_run_plan.get("plan_item_count") or len(raw_items)),
        "linked_item_count": len(items),
        "action_counts": dict(sorted(action_counts.items())),
        "evidence_status_counts": dict(sorted(status_counts.items())),
        "manifest_status_counts": dict(sorted(manifest_counts.items())),
        "source_status_counts": dict(sorted(source_counts.items())),
        "writer_status_counts": dict(sorted(writer_counts.items())),
        "items": items,
        "privacy_note": (
            "Evidence linker reads source-code paths and manifest metadata only. It skips memory, runtime, "
            "tests, ops, logs, and store bodies when building source references, and it does not read or print "
            "memory bodies, JSON/JSONL bodies, raw QQ payloads, tokens, timestamp values, or secrets."
        ),
    }


def link_plan_item(
    item: dict[str, Any],
    *,
    manifest_index: dict[str, list[str]],
    source_index: dict[str, list[str]],
    writer_index: dict[str, list[str]],
    max_examples: int,
) -> dict[str, Any]:
    path = str(item.get("path", ""))
    app_path = app_rel(path)
    source_examples = list(source_index.get(path) or [])[:max_examples]
    writer_examples = list(writer_index.get(path) or [])[:max_examples]
    manifest_examples = list(manifest_index.get(app_path) or [])[:max_examples]
    action = evidence_action(item, writer_examples=writer_examples, manifest_examples=manifest_examples)
    return {
        "priority": str(item.get("priority", "")),
        "path": path,
        "issue_class": str(item.get("issue_class", "")),
        "schema_bucket": str(item.get("schema_bucket", "")),
        "proposed_strategy": str(item.get("proposed_strategy", "")),
        "required_evidence_source": str(item.get("required_evidence_source", "")),
        "safety_status": str(item.get("safety_status", "")),
        "evidence_action": action,
        "evidence_status": evidence_status(
            item,
            action=action,
            source_examples=source_examples,
            manifest_examples=manifest_examples,
            writer_examples=writer_examples,
        ),
        "source_status": "source_reference_found" if source_examples else "no_source_reference",
        "source_reference_count": len(source_index.get(path) or []),
        "source_reference_examples": source_examples,
        "writer_status": "writer_reference_found" if writer_examples else "no_writer_reference",
        "writer_reference_count": len(writer_index.get(path) or []),
        "writer_reference_examples": writer_examples,
        "manifest_status": "manifest_reference_found" if manifest_examples else "no_manifest_reference",
        "manifest_reference_count": len(manifest_index.get(app_path) or []),
        "manifest_reference_examples": manifest_examples,
        "required_followup": required_followup(action),
        "write_allowed": False,
    }


def evidence_action(
    item: dict[str, Any],
    *,
    writer_examples: list[str],
    manifest_examples: list[str],
) -> str:
    issue_class = str(item.get("issue_class", ""))
    zone = str(item.get("zone", ""))
    bucket = str(item.get("schema_bucket", ""))
    if issue_class == "metadata_timestamp_review" and zone == "legacy.data":
        return "auto_exclude_policy_candidate"
    if writer_examples:
        return "writer_fix_candidate"
    if manifest_examples:
        return "manual_data_review_required"
    if bucket == "creative_revision_snapshot":
        return "manual_data_review_required"
    if issue_class == "invalid_timestamp_manual_review":
        return "manual_data_review_required"
    return "blocked_no_evidence"


def evidence_status(
    item: dict[str, Any],
    *,
    action: str,
    source_examples: list[str],
    manifest_examples: list[str],
    writer_examples: list[str],
) -> str:
    if writer_examples and manifest_examples:
        return "writer_and_manifest_evidence"
    if writer_examples:
        return "writer_reference_found"
    if source_examples and manifest_examples:
        return "source_and_manifest_reference"
    if source_examples:
        return "source_reference_only"
    if manifest_examples:
        return "manifest_boundary_found"
    if action == "auto_exclude_policy_candidate":
        return "policy_candidate_without_body_review"
    if str(item.get("schema_bucket", "")) == "creative_revision_snapshot":
        return "path_provenance_candidate_only"
    return "no_evidence_found"


def required_followup(action: str) -> str:
    if action == "auto_exclude_policy_candidate":
        return "Add or confirm an audit exclusion policy; do not backfill human memory timestamps for this metadata."
    if action == "writer_fix_candidate":
        return "Inspect the writer and make future writes include event time; do not rewrite old bodies from this report."
    if action == "manual_data_review_required":
        return "Review schema owner, manifest, or path provenance before any edit."
    return "Keep blocked until a source writer, manifest owner, or explicit exclusion policy is found."


def build_manifest_path_index(app_root: Path) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    stores = Path(app_root) / "stores"
    if not stores.exists():
        return index
    for path in sorted(stores.glob("*manifest*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
        except (OSError, json.JSONDecodeError):
            continue
        manifest_id = str(data.get("manifest_id") or f"stores/{path.name}") if isinstance(data, dict) else f"stores/{path.name}"
        for candidate in collect_manifest_path_strings(data):
            normalized = candidate.replace("\\", "/").strip()
            if normalized:
                index.setdefault(normalized, []).append(manifest_id)
    return {key: sorted(dict.fromkeys(values)) for key, values in index.items()}


def collect_manifest_path_strings(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"path", "projection_paths", "allowed_raw_readers"}:
                yield from collect_manifest_path_strings(child)
            elif isinstance(child, (dict, list)):
                yield from collect_manifest_path_strings(child)
        return
    if isinstance(value, list):
        for child in value:
            yield from collect_manifest_path_strings(child)
        return
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(("memory/", "runtime/", "stores/")) or text.endswith((".py", ".ps1")):
            yield text


def build_source_reference_index(app_root: Path, paths: list[str]) -> dict[str, dict[str, list[str]]]:
    source_files = list(iter_source_files(app_root))
    source_references: dict[str, list[str]] = {path: [] for path in paths}
    writer_references: dict[str, list[str]] = {path: [] for path in paths}
    needles_by_path = {path: reference_needles(path) for path in paths}
    for source_path in source_files:
        try:
            text = source_path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        rel = rel_to_app(app_root, source_path)
        writer_source = is_potential_writer_source(rel, text)
        for path, needles in needles_by_path.items():
            if any(needle and needle in text for needle in needles):
                source_references[path].append(rel)
                if writer_source:
                    writer_references[path].append(rel)
    return {
        "source": {path: sorted(dict.fromkeys(examples)) for path, examples in source_references.items()},
        "writer": {path: sorted(dict.fromkeys(examples)) for path, examples in writer_references.items()},
    }


def is_potential_writer_source(rel_path: str, text: str) -> bool:
    normalized = rel_path.replace("\\", "/").lower()
    if normalized.endswith("_manifest.py"):
        return False
    if normalized.startswith("custom/") and "manifest" in Path(normalized).name:
        return False
    lowered = text.lower()
    return any(token in lowered for token in WRITER_TOKENS)


def iter_source_files(app_root: Path) -> Iterable[Path]:
    root = Path(app_root)
    pending = [root]
    while pending:
        current = pending.pop()
        try:
            children = sorted(current.iterdir(), key=lambda item: item.as_posix().lower())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if child.name in SKIP_SOURCE_DIRS:
                    continue
                pending.append(child)
                continue
            if not child.is_file() or child.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            if child.name.endswith("_manifest.py"):
                continue
            try:
                if child.stat().st_size > MAX_SOURCE_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield child


def reference_needles(path: str) -> list[str]:
    rel = app_rel(path)
    needles = [rel, rel.replace("/", "\\")]
    return [needle for needle in dict.fromkeys(needles) if needle]


def app_rel(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    prefix = APP_REL.as_posix() + "/"
    if normalized.startswith(prefix):
        return normalized[len(prefix) :]
    return normalized


def rel_to_app(app_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(Path(app_root).resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# XinYu Timestamp Evidence Linker",
        "",
        result["privacy_note"],
        "",
        f"- status: {result['status']}",
        f"- source_status: {result['source_status']}",
        f"- source_plan_item_count: {result['source_plan_item_count']}",
        f"- linked_item_count: {result['linked_item_count']}",
        "",
        "## Action Counts",
        "",
    ]
    append_counts(lines, result.get("action_counts") or {})
    lines.extend(["", "## Evidence Status Counts", ""])
    append_counts(lines, result.get("evidence_status_counts") or {})
    lines.extend(["", "## Items", ""])
    items = result.get("items") or []
    if not items:
        lines.append("- none")
    else:
        for item in items:
            lines.append(
                f"- `{item['path']}` | priority={item['priority']} | class={item['issue_class']} | "
                f"bucket={item['schema_bucket']} | action={item['evidence_action']} | "
                f"evidence={item['evidence_status']} | writer_refs={item['writer_reference_count']} | "
                f"source_refs={item['source_reference_count']} | "
                f"manifest_refs={item['manifest_reference_count']} | write_allowed=false"
            )
            if item.get("writer_reference_examples"):
                lines.append("  - writer_reference_examples:")
                for example in item["writer_reference_examples"]:
                    lines.append(f"    - `{example}`")
            if item.get("source_reference_examples"):
                lines.append("  - source_reference_examples:")
                for example in item["source_reference_examples"]:
                    lines.append(f"    - `{example}`")
            if item.get("manifest_reference_examples"):
                lines.append("  - manifest_reference_examples:")
                for example in item["manifest_reference_examples"]:
                    lines.append(f"    - `{example}`")
            lines.append(f"  - followup: {item['required_followup']}")
    return "\n".join(lines).rstrip() + "\n"


def append_counts(lines: list[str], counts: dict[str, int]) -> None:
    if not counts:
        lines.append("- none")
        return
    for name, count in counts.items():
        lines.append(f"- {name}: {count}")


def load_dry_run_plan(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {"status": "missing_or_invalid_dry_run_plan", "items": []}
    return data if isinstance(data, dict) else {"status": "invalid_dry_run_plan_shape", "items": []}


def main() -> int:
    parser = argparse.ArgumentParser(description="Link timestamp dry-run items to source/manifest evidence.")
    parser.add_argument("--dry-run-json", type=Path, default=DEFAULT_DRY_RUN_JSON)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--app-root", type=Path, default=APP_ROOT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-examples", type=int, default=6)
    args = parser.parse_args()

    result = build_timestamp_evidence_links(
        load_dry_run_plan(args.dry_run_json),
        repo_root=args.repo_root,
        app_root=args.app_root,
        max_examples=max(0, args.max_examples),
    )
    output = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if args.json else render_markdown(result)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
