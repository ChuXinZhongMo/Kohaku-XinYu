from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from memory_library_cases_audit import APP_REL, BoundaryRecord, collect_boundary_records


STRUCTURED_CONCERN = "structured_data_inside_memory_review"
ORPHAN_RUNTIME_STATE_HOLD_RELS = {
    "memory/consolidation_state.json",
    "memory/initiative.json",
    "memory/initiative_state.json",
    "memory/maintenance_schedule.json",
    "memory/mind_loop_state.json",
    "memory/personality_change_state.json",
    "memory/personality_self_review_state.json",
    "memory/question_pipeline.json",
    "memory/reflection/closed_loop_state.json",
    "memory/runtime_bridge.json",
    "memory/runtime_bridge_state.json",
}


@dataclass(frozen=True)
class TriageRule:
    category: str
    initial_decision: str
    target_boundary: str
    handling: str


def build_p0_triage(repo_root: Path, max_reference_examples: int = 8) -> dict[str, object]:
    records = [
        record
        for record in collect_boundary_records(repo_root)
        if record.concern == STRUCTURED_CONCERN
    ]
    reference_index = build_reference_index(repo_root, [record.path for record in records])
    items = [
        triage_record(
            repo_root,
            record,
            max_reference_examples=max_reference_examples,
            reference_index=reference_index,
        )
        for record in records
    ]
    items.sort(key=lambda item: (str(item["category"]), str(item["path"])))
    return {
        "total_p0_items": len(items),
        "by_category": dict(sorted(Counter(str(item["category"]) for item in items).items())),
        "by_initial_decision": dict(sorted(Counter(str(item["initial_decision"]) for item in items).items())),
        "items": items,
        "privacy_note": "Generated from paths and source-code reference file names only; structured memory bodies are not read or printed.",
    }


def triage_record(
    repo_root: Path,
    record: BoundaryRecord,
    max_reference_examples: int = 8,
    reference_index: dict[str, list[str]] | None = None,
) -> dict[str, object]:
    rule = rule_for_path(record.path)
    references = (
        reference_result_from_index(reference_index, record.path, max_examples=max_reference_examples)
        if reference_index is not None
        else find_reference_files(repo_root, record.path, max_examples=max_reference_examples)
    )
    decision = rule.initial_decision
    if references["count"] > 0 and decision in {"archive_candidate", "migrate_candidate"}:
        decision = f"{decision}_after_caller_update"
    return {
        "path": record.path,
        "zone": record.zone,
        "category": rule.category,
        "initial_decision": decision,
        "target_boundary": rule.target_boundary,
        "handling": rule.handling,
        "reference_count": references["count"],
        "reference_examples": references["examples"],
        "safe_default": "keep_in_place_until_reviewed",
    }


def rule_for_path(path: str) -> TriageRule:
    rel = _app_rel(path)
    name = Path(rel).name
    lower = rel.lower()

    if name == "safe_extracts.jsonl":
        return TriageRule(
            category="source_extract_log",
            initial_decision="compat_source_extract_store_exists",
            target_boundary="stores/source_extracts",
            handling="Safe source extracts have an explicit store owner; keep the legacy path as compatibility storage and do not migrate bodies without review.",
        )
    if name == "daily_digest.json":
        return TriageRule(
            category="durable_runtime_state",
            initial_decision="compat_store_owner_exists",
            target_boundary="stores/daily_digest_state",
            handling="Daily digest JSON has an explicit store owner; keep the legacy path as compatibility storage while callers depend on the store boundary.",
        )
    if name == "impulse_soup_state.json":
        return TriageRule(
            category="durable_runtime_state",
            initial_decision="compat_store_owner_exists",
            target_boundary="stores/impulse_soup_state",
            handling="Impulse soup JSON has an explicit store owner; keep the legacy path as compatibility storage while callers depend on the store boundary.",
        )
    if name == "slow_state_modulator_state.json":
        return TriageRule(
            category="durable_runtime_state",
            initial_decision="compat_store_owner_exists",
            target_boundary="stores/slow_state_modulator_state",
            handling="Slow state modulator JSON has an explicit store owner; keep the legacy path as compatibility storage while callers depend on the store boundary.",
        )
    if name == "sticker_send_state.generated.json":
        return TriageRule(
            category="durable_runtime_state",
            initial_decision="compat_store_owner_exists",
            target_boundary="stores/sticker_send_state",
            handling="Generated sticker send state has an explicit store owner; keep the legacy path as compatibility storage while callers depend on the store boundary.",
        )
    if name == "owner_recent_events.jsonl":
        return TriageRule(
            category="private_relationship_event_log",
            initial_decision="manifested_private_event_log",
            target_boundary="stores/event_boundary_manifest",
            handling="Private relationship event log has metadata-only manifest ownership; keep in place and do not migrate bodies without review.",
        )
    if name in {"interaction_journal.jsonl", "proactive_request_history.jsonl"}:
        return TriageRule(
            category="episodic_event_log",
            initial_decision="manifested_compat_event_log",
            target_boundary="stores/event_boundary_manifest",
            handling="Episodic event log has metadata-only manifest ownership; keep in place and do not migrate bodies without review.",
        )
    if name == "impulse_soup_trace.jsonl":
        return TriageRule(
            category="runtime_trace_log",
            initial_decision="manifested_runtime_trace_log",
            target_boundary="stores/runtime_trace_manifest",
            handling="Impulse soup trace has metadata-only runtime trace manifest ownership; keep in place and do not migrate bodies without review.",
        )
    if name == "life_event_trace.jsonl":
        return TriageRule(
            category="runtime_trace_log",
            initial_decision="manifested_runtime_trace_log",
            target_boundary="stores/runtime_trace_manifest",
            handling="Life event trace has metadata-only runtime trace manifest ownership; keep in place and do not migrate bodies without review.",
        )
    if name.endswith("_trace.jsonl") or "trace" in name:
        return TriageRule(
            category="runtime_trace_log",
            initial_decision="archive_candidate",
            target_boundary="runtime/logs-or-archive",
            handling="Trace logs should not be canonical memory; archive only after caller checks.",
        )
    if name.endswith("_history.jsonl") or name.endswith("_journal.jsonl") or "events" in name:
        return TriageRule(
            category="episodic_event_log",
            initial_decision="keep_until_event_boundary_is_defined",
            target_boundary="memory/events-or-stores",
            handling="Event logs need an explicit event boundary before migration.",
        )
    if name == "self_action_gateway_approval_queue.jsonl":
        return TriageRule(
            category="runtime_queue",
            initial_decision="compat_store_owner_exists",
            target_boundary="stores/self_action_queue",
            handling="Self-action approval queue has an explicit store owner; keep the legacy path as compatibility storage while callers depend on the store boundary.",
        )
    if name == "qq_outbox_queue.json":
        return TriageRule(
            category="runtime_queue",
            initial_decision="manifested_private_runtime_queue",
            target_boundary="stores/queue_boundary_manifest",
            handling="QQ outbox queue has metadata-only queue manifest ownership; keep in place and do not migrate private queue bodies without a dedicated producer/consumer migration plan.",
        )
    if name == "private_ecosystem_grants.json":
        return TriageRule(
            category="durable_runtime_state",
            initial_decision="compat_store_owner_exists",
            target_boundary="stores/private_ecosystem_grants",
            handling="Private ecosystem grants are owner-approved durable runtime state; keep the legacy path as compatibility storage while callers depend on the store boundary.",
        )
    if "queue" in name:
        return TriageRule(
            category="runtime_queue",
            initial_decision="migrate_candidate",
            target_boundary="stores/queues-or-runtime",
            handling="Queues are operational state; migrate only after producers and consumers are updated together.",
        )
    if name in {"review_inbox_cursor.json", "review_inbox_decisions.json"}:
        return TriageRule(
            category="runtime_cursor_or_decision_store",
            initial_decision="compat_store_owner_exists",
            target_boundary="stores/review_state",
            handling="Review inbox cursor/decision JSON has an explicit store owner; keep the legacy path as compatibility storage while callers depend on the store boundary.",
        )
    if any(marker in name for marker in ("cursor", "decisions")):
        return TriageRule(
            category="runtime_cursor_or_decision_store",
            initial_decision="migrate_candidate",
            target_boundary="stores/review_state",
            handling="Cursor/decision JSON is durable state, not recall memory; move only with the owning service.",
        )
    if lower in ORPHAN_RUNTIME_STATE_HOLD_RELS:
        return TriageRule(
            category="durable_runtime_state",
            initial_decision="held_orphan_runtime_state",
            target_boundary="stores/orphan_runtime_state_manifest",
            handling="Zero-reference runtime state is explicitly held for owner/archive review; deletion is not allowed without manual decision.",
        )
    if name.endswith("_state.json") or name in {
        "consolidation_state.json",
        "daily_digest.json",
        "initiative_state.json",
        "maintenance_schedule.json",
        "personality_change_state.json",
        "personality_self_review_state.json",
        "question_pipeline.json",
        "runtime_bridge.json",
        "runtime_bridge_state.json",
    }:
        return TriageRule(
            category="durable_runtime_state",
            initial_decision="migrate_candidate",
            target_boundary="stores/runtime_state",
            handling="State JSON should be owned by a store/service; keep in place until the owner module migrates.",
        )
    if "goldmark" in lower or "overlay" in name:
        return TriageRule(
            category="persona_runtime_overlay",
            initial_decision="compat_store_owner_exists",
            target_boundary="stores/persona_runtime_overlay",
            handling="Persona/runtime overlay has an explicit store owner; keep the legacy path as compatibility storage while callers depend on the store boundary.",
        )
    return TriageRule(
        category="manual_structured_memory_review",
        initial_decision="manual_review",
        target_boundary="manual",
        handling="No path rule matched; review manually before changing boundaries.",
    )


def build_reference_index(repo_root: Path, paths: list[str]) -> dict[str, list[str]]:
    app = repo_root / APP_REL
    needles_by_path = {path: _reference_needles(path) for path in paths}
    all_needles = sorted({needle for needles in needles_by_path.values() for needle in needles if needle})
    if not all_needles:
        return {path: [] for path in paths}

    command = [
        "rg",
        "--no-ignore",
        "--files-with-matches",
        "--fixed-strings",
        "--glob",
        "!memory/**",
        "--glob",
        "!runtime/**",
        "--glob",
        "!tests/**",
        "--glob",
        "!ops/validation/**",
        "--glob",
        "!ops/manual/**",
        "--glob",
        "!logs/**",
        "--glob",
        "!project-plans/**",
        "--glob",
        "!__pycache__/**",
        "--glob",
        "!.pytest_cache/**",
        "--glob",
        "!*.md",
        "--glob",
        "!*.env",
    ]
    for needle in all_needles:
        command.extend(["-e", needle])
    command.append(".")
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(app),
    )
    if completed.returncode not in {0, 1}:
        return {path: [] for path in paths}

    index: dict[str, list[str]] = {path: [] for path in paths}
    for raw in completed.stdout.splitlines():
        path_obj = app / raw
        if not _is_live_reference(repo_root, path_obj):
            continue
        rel = _rel(repo_root, path_obj)
        text = _read_reference_text(path_obj)
        if not text:
            continue
        for path, needles in needles_by_path.items():
            if any(needle in text for needle in needles):
                index[path].append(rel)
    return {path: sorted(dict.fromkeys(examples)) for path, examples in index.items()}


def reference_result_from_index(
    reference_index: dict[str, list[str]] | None,
    path: str,
    max_examples: int = 8,
) -> dict[str, object]:
    examples = list((reference_index or {}).get(path, []))
    return {"count": len(examples), "examples": examples[:max_examples]}


def find_reference_files(repo_root: Path, path: str, max_examples: int = 8) -> dict[str, object]:
    app = repo_root / APP_REL
    needles = _reference_needles(path)
    examples: list[str] = []
    for needle in needles:
        completed = subprocess.run(
            [
                "rg",
                "--no-ignore",
                "--files-with-matches",
                "--fixed-strings",
                "--glob",
                "!memory/**",
                "--glob",
                "!runtime/**",
                "--glob",
                "!__pycache__/**",
                "--glob",
                "!.pytest_cache/**",
                needle,
                str(app),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode not in {0, 1}:
            continue
        for raw in completed.stdout.splitlines():
            path_obj = Path(raw)
            if not _is_live_reference(repo_root, path_obj):
                continue
            rel = _rel(repo_root, path_obj)
            if rel not in examples:
                examples.append(rel)
    if not examples:
        examples.extend(_fallback_reference_files(repo_root, app, needles))
    return {"count": len(examples), "examples": examples[:max_examples]}


def _read_reference_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _fallback_reference_files(repo_root: Path, app: Path, needles: list[str]) -> list[str]:
    allowed_suffixes = {".py", ".yaml", ".yml", ".ps1", ".ts", ".tsx", ".js"}
    skip_dirs = {
        ".git",
        ".pytest_cache",
        "__pycache__",
        "memory",
        "runtime",
        "node_modules",
        "dist",
        "build",
    }
    matches: list[str] = []
    if not app.exists():
        return matches
    pending = [app]
    while pending:
        current = pending.pop()
        try:
            children = sorted(current.iterdir(), key=lambda item: item.as_posix().lower())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if child.name in skip_dirs:
                    continue
                pending.append(child)
                continue
            if child.suffix.lower() not in allowed_suffixes:
                continue
            if not _is_live_reference(repo_root, child):
                continue
            try:
                text = child.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            if any(needle in text for needle in needles):
                matches.append(_rel(repo_root, child))
    return matches


def _is_live_reference(repo_root: Path, path: Path) -> bool:
    rel = _app_rel(_rel(repo_root, path))
    if rel.startswith(
        (
            "memory/",
            "runtime/",
            "tests/",
            "ops/validation/",
            "ops/manual/",
            "logs/",
            "project-plans/",
        )
    ):
        return False
    if Path(rel).suffix.lower() == ".md":
        return False
    return True


def render_markdown(triage: dict[str, object]) -> str:
    lines = [
        "# XinYu Structured Memory P0 Triage",
        "",
        "Generated from paths plus source-code reference file names only.",
        "It does not read or print JSON/JSONL memory bodies, raw QQ content, tokens, or secrets.",
        "",
        f"- total_p0_items: {triage['total_p0_items']}",
        "",
        "## Category Counts",
        "",
    ]
    for category, count in (triage.get("by_category") or {}).items():
        lines.append(f"- {category}: {count}")
    lines.extend(["", "## Initial Decision Counts", ""])
    for decision, count in (triage.get("by_initial_decision") or {}).items():
        lines.append(f"- {decision}: {count}")
    lines.extend(["", "## Items", ""])
    for item in triage.get("items") or []:
        lines.append(
            f"- `{item['path']}` | category={item['category']} | decision={item['initial_decision']} | "
            f"target={item['target_boundary']} | refs={item['reference_count']}"
        )
        examples = item.get("reference_examples") or []
        if examples:
            lines.append("  - reference_examples:")
            for example in examples:
                lines.append(f"    - `{example}`")
        lines.append(f"  - handling: {item['handling']}")
    lines.extend(
        [
            "",
            "## Safety Rule",
            "",
            "- Keep every item in place until its owning module and fallback behavior are reviewed.",
            "- This is a triage report, not a move/delete instruction.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _reference_needles(path: str) -> list[str]:
    rel = _app_rel(path)
    slash = rel.replace("\\", "/")
    backslash = slash.replace("/", "\\")
    name = Path(slash).name
    needles = [slash, backslash]
    if name not in needles:
        needles.append(name)
    return needles


def _app_rel(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    prefix = APP_REL.as_posix() + "/"
    if normalized.startswith(prefix):
        return normalized[len(prefix) :]
    return normalized


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Triage structured JSON/JSONL files under XinYu memory.")
    parser.add_argument("--repo-root", default="D:\\XinYu")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default="")
    parser.add_argument("--max-reference-examples", type=int, default=8)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    triage = build_p0_triage(Path(args.repo_root), max_reference_examples=args.max_reference_examples)
    rendered = json.dumps(triage, ensure_ascii=False, indent=2) + "\n" if args.json else render_markdown(triage)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
