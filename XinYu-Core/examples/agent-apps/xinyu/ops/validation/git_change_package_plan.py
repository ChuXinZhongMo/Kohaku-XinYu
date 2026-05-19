from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from git_change_group_audit import ChangeEntry, classify_change, collect_git_status, parse_short_status


@dataclass(frozen=True)
class PackageSpec:
    package_id: str
    title: str
    groups: tuple[str, ...]
    intent: str
    risk: str
    handling: str
    validation: tuple[str, ...]


PACKAGE_SPECS: tuple[PackageSpec, ...] = (
    PackageSpec(
        package_id="P00",
        title="docs-worklogs-plans",
        groups=("docs",),
        intent="Keep plans, runbooks, and human audit notes reviewable apart from code behavior.",
        risk="low",
        handling="Review for accuracy and encoding; no runtime behavior should depend on this package.",
        validation=("git diff --check",),
    ),
    PackageSpec(
        package_id="P01",
        title="ops-validation-tools",
        groups=("ops",),
        intent="Keep validation, smoke, and operational tooling together.",
        risk="medium",
        handling="Run focused pytest for each new tool and regenerate reports from the CLI.",
        validation=(
            ".\\.venv\\Scripts\\python.exe -m pytest tests\\test_git_change_group_audit.py tests\\test_git_change_package_plan.py tests\\test_memory_library_cases_audit.py -q",
            ".\\.venv\\Scripts\\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300",
        ),
    ),
    PackageSpec(
        package_id="P02",
        title="tests-smokes-regression",
        groups=("tests",),
        intent="Keep regression coverage changes separate from implementation changes.",
        risk="medium",
        handling="Run the targeted tests first, then the full app test suite before accepting.",
        validation=(".\\.venv\\Scripts\\python.exe -m pytest tests -q",),
    ),
    PackageSpec(
        package_id="P03",
        title="core-runtime-services-stores",
        groups=("core", "services", "stores"),
        intent="Review live runtime behavior, memory recall, persona runtime, services, and stores as one behavior package.",
        risk="high",
        handling="Require focused tests plus full pytest and quick smoke; avoid mixing unrelated cleanup here.",
        validation=(
            ".\\.venv\\Scripts\\python.exe -m pytest tests -q",
            ".\\.venv\\Scripts\\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300",
        ),
    ),
    PackageSpec(
        package_id="P04",
        title="adapters-bridges-io",
        groups=("adapters",),
        intent="Review bridge, QQ, desktop action, and external I/O boundaries separately from core logic.",
        risk="high",
        handling="Validate route contracts and smoke flows without printing tokens, QQ payload bodies, or private memory.",
        validation=(
            ".\\.venv\\Scripts\\python.exe -m pytest tests -q",
            ".\\.venv\\Scripts\\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300",
        ),
    ),
    PackageSpec(
        package_id="P05",
        title="desktop-shell",
        groups=("desktop",),
        intent="Keep Electron/main/preload/renderer changes in one frontend package.",
        risk="medium",
        handling="Run desktop typecheck and build from D:\\XinYu\\XinYu_Desktop.",
        validation=("npm run typecheck", "npm run build"),
    ),
    PackageSpec(
        package_id="P06",
        title="memory-data-review-only",
        groups=("memory-data",),
        intent="Review memory, library, cases, seeds, and legacy data boundaries without exposing private content bodies.",
        risk="high",
        handling="Do not auto-delete or move private data. Use boundary audit reports and make per-file decisions.",
        validation=(
            ".\\.venv\\Scripts\\python.exe ops\\validation\\memory_library_cases_audit.py --repo-root D:\\XinYu --output D:\\XinYu\\worklog\\xinyu-memory-library-cases-boundary-audit-2026-05-18.md",
        ),
    ),
    PackageSpec(
        package_id="P07",
        title="archive-delete-candidates",
        groups=("archive/delete",),
        intent="Review removed or archived smoke/manual/diagnostic files as cleanup candidates.",
        risk="medium",
        handling="Confirm references are gone before accepting deletion; never restore or delete by bulk command.",
        validation=("rg \"<candidate module/function>\" D:\\XinYu\\XinYu-Core\\examples\\agent-apps\\xinyu",),
    ),
    PackageSpec(
        package_id="P99",
        title="unknown-triage",
        groups=("unknown",),
        intent="Isolate paths that do not match current classification rules.",
        risk="unknown",
        handling="Classify these paths before accepting any package that depends on them.",
        validation=("Manual path classification review.",),
    ),
)

PACKAGE_BY_GROUP = {
    group: spec
    for spec in PACKAGE_SPECS
    for group in spec.groups
}


def build_package_plan(entries: list[ChangeEntry], max_examples: int = 10) -> dict[str, object]:
    buckets: dict[str, list[tuple[ChangeEntry, str]]] = defaultdict(list)
    for entry in entries:
        group = classify_change(entry.path, entry.status)
        spec = PACKAGE_BY_GROUP.get(group, PACKAGE_BY_GROUP["unknown"])
        buckets[spec.package_id].append((entry, group))

    packages: list[dict[str, object]] = []
    for spec in PACKAGE_SPECS:
        items = buckets.get(spec.package_id, [])
        if not items:
            continue
        status_counts = Counter(_status_label(entry.status) for entry, _group in items)
        group_counts = Counter(group for _entry, group in items)
        packages.append(
            {
                "id": spec.package_id,
                "title": spec.title,
                "risk": spec.risk,
                "intent": spec.intent,
                "handling": spec.handling,
                "groups": dict(sorted(group_counts.items())),
                "status": dict(sorted(status_counts.items())),
                "count": len(items),
                "validation": list(spec.validation),
                "examples": [entry.path for entry, _group in items[:max_examples]],
            }
        )

    return {
        "total": len(entries),
        "package_count": len(packages),
        "packages": packages,
        "review_order": [package["id"] for package in packages],
        "privacy_note": "Generated from git status paths only; does not read or print private memory bodies.",
    }


def render_markdown(plan: dict[str, object]) -> str:
    lines = [
        "# XinYu Change Package Plan",
        "",
        "Generated from `git status --short` paths only.",
        "It does not read or print private memory, raw QQ content, tokens, or secrets.",
        "",
        f"- total_entries: {plan['total']}",
        f"- package_count: {plan['package_count']}",
        f"- review_order: {', '.join(str(item) for item in plan.get('review_order', []))}",
        "",
        "## Packages",
        "",
    ]
    for package in plan.get("packages", []):
        assert isinstance(package, dict)
        lines.append(f"### {package['id']} {package['title']}")
        lines.append(f"- risk: {package['risk']}")
        lines.append(f"- count: {package['count']}")
        lines.append(f"- intent: {package['intent']}")
        lines.append(f"- handling: {package['handling']}")
        lines.append("- groups:")
        for group, count in (package.get("groups") or {}).items():
            lines.append(f"  - {group}: {count}")
        lines.append("- status:")
        for status, count in (package.get("status") or {}).items():
            lines.append(f"  - {status}: {count}")
        lines.append("- validation:")
        for command in package.get("validation") or []:
            lines.append(f"  - `{command}`")
        examples = package.get("examples") or []
        if examples:
            lines.append("- examples:")
            for example in examples:
                lines.append(f"  - `{example}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _status_label(status: str) -> str:
    clean = status.strip()
    if clean == "??":
        return "untracked"
    if "D" in status:
        return "deleted"
    if "A" in status:
        return "added"
    if "M" in status:
        return "modified"
    if "R" in status:
        return "renamed"
    return clean or "unknown"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan XinYu dirty worktree review packages.")
    parser.add_argument("--repo-root", default="D:\\XinYu")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default="")
    parser.add_argument("--max-examples", type=int, default=10)
    parser.add_argument(
        "--from-status-file",
        default="",
        help="Optional text file containing git status --short output for deterministic tests.",
    )
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    if args.from_status_file:
        entries = parse_short_status(Path(args.from_status_file).read_text(encoding="utf-8"))
    else:
        entries = collect_git_status(Path(args.repo_root))
    plan = build_package_plan(entries, max_examples=args.max_examples)
    rendered = json.dumps(plan, ensure_ascii=False, indent=2) + "\n" if args.json else render_markdown(plan)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
