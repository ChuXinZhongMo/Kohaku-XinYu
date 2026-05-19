from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from archive_delete_reference_audit import build_archive_delete_reference_audit
from boundary_readiness_audit import build_boundary_readiness_audit
from git_change_group_audit import ChangeEntry, collect_git_status, parse_short_status, summarize
from git_change_package_plan import build_package_plan


REVIEW_ACTION_BY_PACKAGE = {
    "P00": "keep_docs_review",
    "P01": "keep_ops_validation",
    "P02": "keep_regression_tests",
    "P03": "merge_review_core_runtime",
    "P04": "merge_review_adapters",
    "P05": "keep_desktop_shell",
    "P06": "keep_memory_data_review_only",
    "P07": "archive_delete_review",
    "P99": "hold_unknown_triage",
}

REQUIRED_VALIDATION = (
    "git diff --check",
    ".\\.venv\\Scripts\\python.exe -m pytest tests -q",
    ".\\.venv\\Scripts\\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300",
    "npm run typecheck",
    "npm run build",
)


def build_commit_readiness_audit(
    repo_root: Path,
    *,
    entries: list[ChangeEntry] | None = None,
    boundary_audit: dict[str, Any] | None = None,
    archive_delete_audit: dict[str, Any] | None = None,
    max_examples: int = 8,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    status_entries = entries if entries is not None else collect_git_status(root)
    package_plan = build_package_plan(status_entries, max_examples=max_examples)
    group_summary = summarize(status_entries)
    archive_audit = (
        archive_delete_audit
        if archive_delete_audit is not None
        else build_archive_delete_reference_audit(root, entries=status_entries, max_examples=max_examples)
    )
    boundary = boundary_audit if boundary_audit is not None else build_boundary_readiness_audit(root)

    packages = list(package_plan.get("packages") or [])
    package_by_id = {str(package.get("id")): package for package in packages if isinstance(package, dict)}
    unknown_entry_count = int((package_by_id.get("P99") or {}).get("count", 0) or 0)
    archive_decisions = dict(archive_audit.get("by_decision") or {})
    archive_hold_count = int(archive_decisions.get("hold_delete_referenced", 0) or 0)
    boundary_status = str(boundary.get("status", "unknown"))

    hold_reasons = _hold_reasons(
        unknown_entry_count=unknown_entry_count,
        archive_hold_count=archive_hold_count,
        boundary_status=boundary_status,
    )
    status = _readiness_status(total_entries=len(status_entries), hold_reasons=hold_reasons)
    package_overview = [_package_overview(package) for package in packages if isinstance(package, dict)]

    return {
        "status": status,
        "total_dirty_entries": len(status_entries),
        "package_count": package_plan.get("package_count", 0),
        "review_order": list(package_plan.get("review_order") or []),
        "unknown_entry_count": unknown_entry_count,
        "risk_package_counts": _risk_package_counts(packages),
        "risk_entry_counts": _risk_entry_counts(packages),
        "group_counts": _group_counts(group_summary),
        "package_overview": package_overview,
        "archive_delete": {
            "total_candidates": archive_audit.get("total_candidates", 0),
            "by_decision": archive_decisions,
            "by_kind": dict(archive_audit.get("by_kind") or {}),
            "hold_count": archive_hold_count,
        },
        "boundary_readiness": {
            "status": boundary_status,
            "manifest_failure_count": boundary.get("manifest_failure_count", 0),
            "reference_failure_count": boundary.get("reference_failure_count", 0),
            "p0_generic_decision_count": (boundary.get("p0") or {}).get("generic_decision_count", 0),
            "held_orphan_count": (boundary.get("orphan_runtime_state_audit") or {}).get("held_orphan_count", 0),
        },
        "recommended_commit_split": _recommended_commit_split(package_overview),
        "closeout_summary": _closeout_summary(package_overview, archive_decisions, hold_reasons),
        "hold_reasons": hold_reasons,
        "remaining_risks": _remaining_risks(package_overview, archive_hold_count, boundary),
        "required_validation": list(REQUIRED_VALIDATION),
        "privacy_note": (
            "Generated from git status paths and existing metadata audits only; does not read or print "
            "private memory bodies, raw QQ payload bodies, tokens, or secrets."
        ),
    }


def render_markdown(audit: dict[str, Any]) -> str:
    boundary = audit.get("boundary_readiness") or {}
    archive = audit.get("archive_delete") or {}
    lines = [
        "# XinYu Commit Readiness Audit",
        "",
        "Generated from `git status --short` paths plus metadata-only validation reports.",
        "It does not read or print private memory bodies, raw QQ payload bodies, tokens, or secrets.",
        "",
        f"- status: {audit['status']}",
        f"- total_dirty_entries: {audit['total_dirty_entries']}",
        f"- package_count: {audit['package_count']}",
        f"- unknown_entry_count: {audit['unknown_entry_count']}",
        f"- boundary_status: {boundary.get('status', '')}",
        f"- archive_delete_holds: {archive.get('hold_count', 0)}",
        "",
        "## Package Overview",
        "",
        "| package | risk | count | action |",
        "| --- | --- | ---: | --- |",
    ]
    for package in audit.get("package_overview") or []:
        lines.append(
            f"| {package['id']} {package['title']} | {package['risk']} | "
            f"{package['count']} | {package['review_action']} |"
        )

    lines.extend(["", "## Review Order", ""])
    for package_id in audit.get("review_order") or []:
        lines.append(f"- `{package_id}`")

    lines.extend(["", "## Archive/Delete Decisions", ""])
    decisions = archive.get("by_decision") or {}
    if decisions:
        for decision, count in sorted(decisions.items()):
            lines.append(f"- {decision}: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Closeout Summary", ""])
    closeout = audit.get("closeout_summary") or {}
    for key in ("kept", "merged", "archived", "deleted", "hold"):
        values = closeout.get(key) or []
        lines.append(f"### {key}")
        if values:
            for value in values:
                lines.append(f"- {value}")
        else:
            lines.append("- none")
        lines.append("")

    lines.extend(["## Remaining Risks", ""])
    risks = audit.get("remaining_risks") or []
    if risks:
        for risk in risks:
            lines.append(f"- {risk}")
    else:
        lines.append("- none")

    lines.extend(["", "## Required Validation", ""])
    for command in audit.get("required_validation") or []:
        lines.append(f"- `{command}`")

    return "\n".join(lines).rstrip() + "\n"


def _hold_reasons(*, unknown_entry_count: int, archive_hold_count: int, boundary_status: str) -> list[str]:
    reasons: list[str] = []
    if unknown_entry_count:
        reasons.append(f"{unknown_entry_count} dirty paths are still in P99 unknown triage.")
    if archive_hold_count:
        reasons.append(f"{archive_hold_count} archive/delete candidates still have live references.")
    if boundary_status != "pass":
        reasons.append(f"boundary readiness status is {boundary_status}.")
    return reasons


def _readiness_status(*, total_entries: int, hold_reasons: list[str]) -> str:
    if total_entries == 0:
        return "clean"
    if hold_reasons:
        return "needs_triage"
    return "ready_for_review"


def _package_overview(package: dict[str, Any]) -> dict[str, Any]:
    package_id = str(package.get("id", ""))
    return {
        "id": package_id,
        "title": package.get("title", ""),
        "risk": package.get("risk", ""),
        "count": package.get("count", 0),
        "groups": dict(package.get("groups") or {}),
        "status": dict(package.get("status") or {}),
        "review_action": REVIEW_ACTION_BY_PACKAGE.get(package_id, "manual_review"),
    }


def _risk_package_counts(packages: list[Any]) -> dict[str, int]:
    counts = Counter()
    for package in packages:
        if isinstance(package, dict):
            counts[str(package.get("risk", "unknown"))] += 1
    return dict(sorted(counts.items()))


def _risk_entry_counts(packages: list[Any]) -> dict[str, int]:
    counts = Counter()
    for package in packages:
        if isinstance(package, dict):
            counts[str(package.get("risk", "unknown"))] += int(package.get("count", 0) or 0)
    return dict(sorted(counts.items()))


def _group_counts(group_summary: dict[str, Any]) -> dict[str, int]:
    groups = group_summary.get("by_group") or {}
    return {
        str(group): int(payload.get("count", 0) or 0)
        for group, payload in sorted(groups.items())
        if isinstance(payload, dict)
    }


def _recommended_commit_split(package_overview: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "package_id": package["id"],
            "title": package["title"],
            "risk": package["risk"],
            "count": package["count"],
            "review_action": package["review_action"],
        }
        for package in package_overview
    ]


def _closeout_summary(
    package_overview: list[dict[str, Any]],
    archive_decisions: dict[str, Any],
    hold_reasons: list[str],
) -> dict[str, list[str]]:
    kept = [
        f"{package['id']} {package['title']} ({package['count']} paths)"
        for package in package_overview
        if package["id"] in {"P00", "P01", "P02", "P05", "P06"}
    ]
    merged = [
        f"{package['id']} {package['title']} ({package['count']} paths)"
        for package in package_overview
        if package["id"] in {"P03", "P04"}
    ]
    archived = []
    relocated = int(archive_decisions.get("accept_delete_relocated", 0) or 0)
    if relocated:
        archived.append(f"{relocated} cleanup deletions have relocated replacements.")
    deleted = []
    no_live_refs = int(archive_decisions.get("accept_delete_no_live_refs", 0) or 0)
    if no_live_refs:
        deleted.append(f"{no_live_refs} cleanup deletions have no live references in the audit.")
    hold = list(hold_reasons)
    return {
        "kept": kept,
        "merged": merged,
        "archived": archived,
        "deleted": deleted,
        "hold": hold,
    }


def _remaining_risks(package_overview: list[dict[str, Any]], archive_hold_count: int, boundary: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    high_risk = [
        f"{package['id']} {package['title']}"
        for package in package_overview
        if package.get("risk") == "high"
    ]
    if high_risk:
        risks.append("High-risk packages need behavior review: " + ", ".join(high_risk) + ".")
    memory_package = next((package for package in package_overview if package.get("id") == "P06"), None)
    if memory_package:
        risks.append("P06 memory-data remains review-only; do not auto-delete or move private bodies.")
    held_orphans = int(((boundary.get("orphan_runtime_state_audit") or {}).get("held_orphan_count", 0)) or 0)
    if held_orphans:
        risks.append(f"{held_orphans} orphan runtime-state paths are intentionally held for manual ownership review.")
    if archive_hold_count:
        risks.append(f"{archive_hold_count} archive/delete candidates require reference cleanup before acceptance.")
    return risks


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aggregate XinYu commit-readiness metadata without reading private bodies.")
    parser.add_argument("--repo-root", default="D:\\XinYu")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default="")
    parser.add_argument("--max-examples", type=int, default=8)
    parser.add_argument("--from-status-file", default="")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    entries = None
    if args.from_status_file:
        entries = parse_short_status(Path(args.from_status_file).read_text(encoding="utf-8"))
    audit = build_commit_readiness_audit(
        Path(args.repo_root),
        entries=entries,
        max_examples=args.max_examples,
    )
    rendered = json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n" if args.json else render_markdown(audit)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if audit["status"] in {"clean", "ready_for_review"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
