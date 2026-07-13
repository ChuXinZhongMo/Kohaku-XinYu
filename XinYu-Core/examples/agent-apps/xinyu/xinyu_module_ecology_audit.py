from __future__ import annotations


__all__ = (
    "SKIP_SCAN_DIRS",
    "SKIP_SCAN_PREFIXES",
)

import argparse
import ast
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from xinyu_module_ecology_audit_store import collect_module_ecology_paths
from xinyu_module_ecology_audit_store import read_module_ecology_git_status_text
from xinyu_module_ecology_audit_store import read_module_ecology_reference_sources
from xinyu_module_ecology_audit_store import read_module_ecology_status_file
from xinyu_module_ecology_audit_store import write_module_ecology_output

from xinyu_module_ecology_audit_store import SKIP_SCAN_DIRS, SKIP_SCAN_PREFIXES

NON_LIVE_REFERENCE_PREFIXES = (
    "tests/",
    "lab/",
    "learning/",
    "ops/archive/",
    "ops/reports/",
    "project-plans/",
)
GENERIC_REFERENCE_STEMS = {
    "app",
    "config",
    "helpers",
    "index",
    "init",
    "main",
    "metadata",
    "models",
    "readme",
    "state",
    "test",
    "tools",
    "types",
    "utils",
}


@dataclass(frozen=True, slots=True)
class ModuleEcologyItem:
    path: str
    bucket: str
    niche: str
    ecology_decision: str
    reference_count: int
    test_count: int
    duplicate_group: str
    activity_signal: str
    retirement_rule: str
    notes: tuple[str, ...] = ()

    def to_report(self) -> dict[str, Any]:
        data = asdict(self)
        data["notes"] = list(self.notes)
        return data


def classify_module_ecology_item(
    path: str | Path,
    *,
    status: str = "",
    reference_count: int = 0,
    test_count: int = 0,
    duplicate_group: str = "",
    canonical_path: str = "",
    imported_by_live: bool = False,
) -> ModuleEcologyItem:
    rel = _norm(path)
    bucket = _bucket_for(rel, status=status)
    niche = _niche_for(rel, bucket)
    refs = max(0, int(reference_count))
    tests = max(0, int(test_count))
    duplicate = _safe(duplicate_group)
    canonical = _norm(canonical_path)
    test_collected = _is_test_runner_collected(rel)
    active = imported_by_live or refs > 0 or tests > 0 or test_collected

    if "D" in status or bucket == "delete":
        decision = "delete_candidate_requires_reference_audit"
        activity = "deleted_in_worktree" if "D" in status else "delete_bucket"
        retirement = "accept only after archive/delete reference audit passes"
    elif duplicate and canonical and canonical != rel:
        decision = "merge_keep_compat_shim"
        activity = f"duplicate_group:{duplicate}; canonical:{canonical}"
        retirement = "keep shim until callers move to canonical owner"
    elif bucket == "archive":
        decision = "archive_keep_historical"
        activity = "historical_or_archived_path"
        retirement = "do not import from live path"
    elif bucket == "lab":
        if active:
            decision = "keep_lab_shadow"
            activity = "test_runner_collected" if test_collected and not (refs or tests) else _activity(active=active, refs=refs, tests=tests)
            retirement = "archive if no validation references remain"
        else:
            decision = "archive_candidate_lab_stale"
            activity = "no_live_refs_or_tests"
            retirement = "move to archive after reference audit"
    elif bucket in {"core", "adapters", "stores", "services", "ops"}:
        if not active:
            decision = "archive_candidate_no_live_refs"
            activity = "no_live_refs_or_tests"
            retirement = "archive before delete; delete only after no-ref audit"
        else:
            decision = "keep_active_niche"
            activity = _activity(active=active, refs=refs, tests=tests)
            retirement = "merge/archive only when a canonical owner replaces this niche"
    else:
        decision = "classify_before_change"
        activity = _activity(active=active, refs=refs, tests=tests) if active else "unknown_activity"
        retirement = "assign bucket before merge/archive/delete"

    return ModuleEcologyItem(
        path=rel,
        bucket=bucket,
        niche=niche,
        ecology_decision=decision,
        reference_count=refs,
        test_count=tests,
        duplicate_group=duplicate or "none",
        activity_signal=activity,
        retirement_rule=retirement,
        notes=(
            "ecology_gardening_mapping",
            "advisory_only_no_file_move_or_delete",
            "no_private_memory_body_output",
        ),
    )


def build_module_ecology_audit(
    root: Path,
    *,
    module_paths: list[str | Path] | tuple[str | Path, ...] | None = None,
    statuses: dict[str, str] | None = None,
    duplicate_groups: dict[str, str] | None = None,
    canonical_paths: dict[str, str] | None = None,
    max_items: int = 500,
) -> dict[str, Any]:
    app_root = root.resolve()
    paths = (
        [_norm(item) for item in module_paths]
        if module_paths is not None
        else collect_module_ecology_paths(app_root, max_items=max_items)
    )
    reference_index = _build_reference_index(app_root)
    statuses = {_norm(key): value for key, value in (statuses or {}).items()}
    if module_paths is None and statuses:
        paths = sorted(set(paths) | set(statuses))
    duplicate_groups = {_norm(key): value for key, value in (duplicate_groups or {}).items()}
    canonical_paths = {_norm(key): _norm(value) for key, value in (canonical_paths or {}).items()}

    items: list[ModuleEcologyItem] = []
    for rel in paths[:max(1, int(max_items))]:
        refs = _reference_count(reference_index, rel)
        tests = _test_reference_count(reference_index, rel)
        items.append(
            classify_module_ecology_item(
                rel,
                status=statuses.get(rel, ""),
                reference_count=refs,
                test_count=tests,
                duplicate_group=duplicate_groups.get(rel, ""),
                canonical_path=canonical_paths.get(rel, ""),
                imported_by_live=refs > 0,
            )
        )

    by_bucket = Counter(item.bucket for item in items)
    by_decision = Counter(item.ecology_decision for item in items)
    return {
        "item_count": len(items),
        "by_bucket": dict(sorted(by_bucket.items())),
        "by_decision": dict(sorted(by_decision.items())),
        "kept": sum(1 for item in items if item.ecology_decision.startswith("keep")),
        "merged": sum(1 for item in items if item.ecology_decision.startswith("merge")),
        "archived": sum(1 for item in items if item.ecology_decision.startswith("archive")),
        "deleted": sum(1 for item in items if item.ecology_decision.startswith("delete")),
        "items": [item.to_report() for item in items],
        "privacy_note": "Generated from file paths and source/doc references only; memory/runtime/data/library/cases bodies are skipped.",
        "remaining_risks": _remaining_risks(items),
    }


def render_module_ecology_report(audit: dict[str, Any]) -> str:
    lines = [
        "# XinYu Module Ecology Audit",
        "",
        "Generated from module paths and source/doc references only.",
        "It does not read or print memory, runtime, QQ payload, library, cases, or data bodies.",
        "",
        f"- item_count: {audit.get('item_count', 0)}",
        f"- kept: {audit.get('kept', 0)}",
        f"- merged: {audit.get('merged', 0)}",
        f"- archived: {audit.get('archived', 0)}",
        f"- deleted: {audit.get('deleted', 0)}",
        "",
        "## Bucket Counts",
        "",
    ]
    for bucket, count in (audit.get("by_bucket") or {}).items():
        lines.append(f"- {bucket}: {count}")
    lines.extend(["", "## Decision Counts", ""])
    for decision, count in (audit.get("by_decision") or {}).items():
        lines.append(f"- {decision}: {count}")
    lines.extend(
        [
            "",
            "## Lifecycle Summary",
            "",
            "- kept: active modules with live references or tests stay in place.",
            "- merged: duplicate/shim modules stay as compatibility entrances until callers move.",
            "- archived: stale lab or unreferenced active-bucket modules need archive-before-delete review.",
            "- deleted: worktree deletions remain candidates until archive/delete reference audit passes.",
            "",
            "## Remaining Risks",
            "",
        ]
    )
    for risk in audit.get("remaining_risks") or ("none",):
        lines.append(f"- {risk}")
    lines.extend(["", "## Items", ""])
    for item in audit.get("items") or []:
        lines.append(
            f"- `{item['path']}` | bucket={item['bucket']} | niche={item['niche']} | "
            f"decision={item['ecology_decision']} | refs={item['reference_count']} | tests={item['test_count']}"
        )
    return "\n".join(lines).rstrip() + "\n"


def filter_module_ecology_audit(
    audit: dict[str, Any],
    *,
    decision_prefixes: tuple[str, ...] = (),
    buckets: tuple[str, ...] = (),
) -> dict[str, Any]:
    prefixes = tuple(prefix for prefix in decision_prefixes if prefix)
    bucket_set = {bucket for bucket in buckets if bucket}
    items = [
        item
        for item in audit.get("items") or []
        if (not prefixes or any(str(item.get("ecology_decision", "")).startswith(prefix) for prefix in prefixes))
        and (not bucket_set or item.get("bucket") in bucket_set)
    ]
    by_bucket = Counter(str(item.get("bucket", "unknown")) for item in items)
    by_decision = Counter(str(item.get("ecology_decision", "unknown")) for item in items)
    return {
        "item_count": len(items),
        "source_item_count": audit.get("item_count", 0),
        "filters": {
            "decision_prefixes": list(prefixes),
            "buckets": sorted(bucket_set),
        },
        "by_bucket": dict(sorted(by_bucket.items())),
        "by_decision": dict(sorted(by_decision.items())),
        "kept": sum(1 for item in items if str(item.get("ecology_decision", "")).startswith("keep")),
        "merged": sum(1 for item in items if str(item.get("ecology_decision", "")).startswith("merge")),
        "archived": sum(1 for item in items if str(item.get("ecology_decision", "")).startswith("archive")),
        "deleted": sum(1 for item in items if str(item.get("ecology_decision", "")).startswith("delete")),
        "items": items,
        "privacy_note": audit.get("privacy_note", ""),
        "remaining_risks": _remaining_risks_for_decisions(by_decision),
    }


def _build_reference_index(app_root: Path) -> list[tuple[str, str, set[str]]]:
    index: list[tuple[str, str, set[str]]] = []
    for rel, text in read_module_ecology_reference_sources(app_root, max_items=5000):
        index.append((rel, text, _python_imports_for_source(rel, text)))
    return index


def _reference_count(reference_index: list[tuple[str, str, set[str]]], rel: str) -> int:
    needles = _reference_needles(rel)
    target_module = _module_name_for_rel(rel)
    count = 0
    for source_rel, text, imports in reference_index:
        if source_rel == rel:
            continue
        if source_rel.startswith(NON_LIVE_REFERENCE_PREFIXES):
            continue
        if _references_target(text, imports, needles, target_module):
            count += 1
    return count


def _test_reference_count(reference_index: list[tuple[str, str, set[str]]], rel: str) -> int:
    needles = _reference_needles(rel)
    target_module = _module_name_for_rel(rel)
    count = 0
    for source_rel, text, imports in reference_index:
        if not source_rel.startswith("tests/"):
            continue
        if _references_target(text, imports, needles, target_module):
            count += 1
    return count


def _references_target(text: str, imports: set[str], needles: tuple[str, ...], target_module: str) -> bool:
    if target_module and target_module in imports:
        return True
    return any(needle and needle in text for needle in needles)


def _reference_needles(rel: str) -> tuple[str, ...]:
    path = Path(rel)
    name = path.name
    stem = path.stem
    needles = [rel, name]
    if path.suffix == ".py":
        needles.append(rel[:-3].replace("/", "."))
    if stem and len(stem) > 3 and stem.lower() not in GENERIC_REFERENCE_STEMS:
        needles.append(stem)
    return tuple(dict.fromkeys(needle for needle in needles if needle))


def _module_name_for_rel(rel: str) -> str:
    return rel[:-3].replace("/", ".") if rel.endswith(".py") else ""


def _python_imports_for_source(rel: str, text: str) -> set[str]:
    if not rel.endswith(".py"):
        return set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    source_module = _module_name_for_rel(rel)
    source_package = source_module.rsplit(".", 1)[0] if not source_module.endswith(".__init__") else source_module[:-9]
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_import_from(source_package, node.module or "", node.level)
            if resolved:
                imports.add(resolved)
            elif node.level:
                resolved = _resolve_import_from(source_package, "", node.level)
            else:
                resolved = ""
            if resolved and not node.module:
                for alias in node.names:
                    if alias.name != "*":
                        imports.add(f"{resolved}.{alias.name}")
    return imports


def _resolve_import_from(source_package: str, module: str, level: int) -> str:
    if level <= 0:
        return module
    package_parts = source_package.split(".") if source_package else []
    keep = max(0, len(package_parts) - (level - 1))
    base = package_parts[:keep]
    if module:
        base.extend(module.split("."))
    return ".".join(part for part in base if part)


def collect_git_statuses(root: Path) -> dict[str, str]:
    app_root = root.resolve()
    return parse_git_short_status(read_module_ecology_git_status_text(app_root))


def parse_git_short_status(text: str) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for line in text.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        rel = _status_path(line[3:])
        if rel:
            statuses[rel] = status
    return statuses


def _status_path(raw: str) -> str:
    rel = raw.strip().strip('"')
    if " -> " in rel:
        rel = rel.split(" -> ", 1)[1].strip().strip('"')
    rel = _norm(rel)
    if rel.startswith("./"):
        rel = rel[2:]
    return rel


def _remaining_risks(items: list[ModuleEcologyItem]) -> list[str]:
    return _remaining_risks_for_decisions(Counter(item.ecology_decision for item in items))


def _remaining_risks_for_decisions(decisions: Counter[str]) -> list[str]:
    risks: list[str] = []
    if decisions.get("delete_candidate_requires_reference_audit"):
        risks.append("delete candidates still require archive/delete reference audit evidence before removal is accepted")
    if decisions.get("archive_candidate_no_live_refs") or decisions.get("archive_candidate_lab_stale"):
        risks.append("archive candidates are advisory until owners confirm they are not active runtime niches")
    if decisions.get("classify_before_change"):
        risks.append("unknown-bucket modules need explicit core/adapters/stores/services/ops/lab/archive/delete classification")
    if decisions.get("merge_keep_compat_shim"):
        risks.append("merge shims need caller migration before compatibility entrances can be removed")
    return risks or ["none"]


def _bucket_for(rel: str, *, status: str = "") -> str:
    name = Path(rel).name
    if "D" in status:
        return "delete"
    if rel.startswith(("archive/", "ops/archive/")):
        return "archive"
    if rel.startswith(("tests/", "lab/", "learning/", "project-plans/")) or name.endswith("_trial.py") or "replay" in name:
        return "lab"
    if rel.startswith(("ops/", "tools/")) or name in {"smoke_run.py", "long_run_status.py", "run_local_xinyu.py"}:
        return "ops"
    if rel.startswith(("stores/", "data/")) or rel == "data/" or name in {"state_service.py", "xinyu_storage_paths.py"}:
        return "stores"
    if rel.startswith("services/") or name in {"xinyu_chat_service.py", "xinyu_codex_service.py", "xinyu_daily_digest.py"}:
        return "services"
    if rel.startswith("custom/"):
        return "core"
    if name.startswith(("xinyu_qq_", "xinyu_bridge_", "xinyu_desktop_")):
        return "adapters"
    if name.startswith("xinyu_") or name.startswith("v1_") or rel.startswith("xinyu_v1/"):
        return "core"
    if name.endswith((".md", ".yaml", ".yml", ".json", ".ps1", ".ini", ".example")):
        return "ops"
    return "unknown"


def _niche_for(rel: str, bucket: str) -> str:
    name = Path(rel).name
    if bucket == "core":
        if "memory" in name or "recall" in name:
            return "memory_or_recall_core"
        if "persona" in name:
            return "persona_core"
        if "emotion" in name:
            return "emotion_core"
        if "triage" in name or "scene" in name or "policy" in name:
            return "turn_policy_core"
        return "live_turn_core"
    if bucket == "adapters":
        return "transport_or_bridge_adapter"
    if bucket == "stores":
        return "persistence_helper_or_manifest"
    if bucket == "services":
        return "runtime_service_helper"
    if bucket == "ops":
        return "operator_validation_or_docs"
    if bucket == "lab":
        return "shadow_experiment_or_test_asset"
    if bucket == "archive":
        return "historical_reference"
    if bucket == "delete":
        return "deleted_cleanup_candidate"
    return "unclassified_niche"


def _activity(*, active: bool, refs: int, tests: int) -> str:
    if not active:
        return "no_activity"
    parts = []
    if refs:
        parts.append(f"live_refs:{refs}")
    if tests:
        parts.append(f"tests:{tests}")
    return ",".join(parts) or "imported_by_live"


def _is_test_runner_collected(rel: str) -> bool:
    path = Path(rel)
    return rel.startswith("tests/") and path.suffix == ".py" and (path.name.startswith("test_") or path.name == "conftest.py")


def _norm(path: str | Path) -> str:
    return str(path).replace("\\", "/").strip().strip('"')


def _safe(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a metadata-only XinYu module ecology audit.")
    parser.add_argument("--root", default=".", help="XinYu app root to scan.")
    parser.add_argument("--max-items", type=int, default=2000)
    parser.add_argument("--json", action="store_true", help="Render JSON instead of Markdown.")
    parser.add_argument("--output", default="", help="Optional output path.")
    parser.add_argument("--status-file", default="", help="Optional git status --short text file.")
    parser.add_argument("--no-git-status", action="store_true", help="Do not merge current git status paths.")
    parser.add_argument(
        "--decision-prefix",
        action="append",
        default=[],
        help="Only include items whose ecology decision starts with this prefix. Repeatable.",
    )
    parser.add_argument("--bucket", action="append", default=[], help="Only include items in this bucket. Repeatable.")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args(argv)
    root = Path(args.root)
    statuses: dict[str, str] = {}
    if not args.no_git_status:
        statuses.update(collect_git_statuses(root))
    if args.status_file:
        statuses.update(parse_git_short_status(read_module_ecology_status_file(Path(args.status_file))))
    audit = build_module_ecology_audit(
        root,
        statuses=statuses,
        max_items=args.max_items,
    )
    if args.decision_prefix or args.bucket:
        audit = filter_module_ecology_audit(
            audit,
            decision_prefixes=tuple(args.decision_prefix),
            buckets=tuple(args.bucket),
        )
    rendered = (
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.json
        else render_module_ecology_report(audit)
    )
    if args.output:
        write_module_ecology_output(Path(args.output), rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
