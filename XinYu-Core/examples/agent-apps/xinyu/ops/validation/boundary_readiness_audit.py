from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from ._validation_paths import ensure_validation_paths
except ImportError:  # pragma: no cover - direct script execution
    from _validation_paths import ensure_validation_paths


APP_ROOT = ensure_validation_paths("ops/validation")
PROJECT_ROOT = APP_ROOT.parents[3]

try:
    from .event_log_boundary_audit import build_event_log_boundary_audit
    from .memory_structured_p0_triage import build_p0_triage
    from .orphan_runtime_state_audit import build_orphan_runtime_state_audit
    from .queue_boundary_audit import build_queue_boundary_audit
    from .runtime_trace_boundary_audit import build_runtime_trace_boundary_audit
    from .validate_event_boundary_manifest import validate_manifest as validate_event_manifest
    from .validate_memory_library_manifest import validate_manifest as validate_memory_manifest
    from .validate_orphan_runtime_state_manifest import validate_manifest as validate_orphan_manifest
    from .validate_queue_boundary_manifest import validate_manifest as validate_queue_manifest
    from .validate_runtime_trace_manifest import validate_manifest as validate_runtime_trace_manifest
except ImportError:  # pragma: no cover - direct script execution
    from event_log_boundary_audit import build_event_log_boundary_audit
    from memory_structured_p0_triage import build_p0_triage
    from orphan_runtime_state_audit import build_orphan_runtime_state_audit
    from queue_boundary_audit import build_queue_boundary_audit
    from runtime_trace_boundary_audit import build_runtime_trace_boundary_audit
    from validate_event_boundary_manifest import validate_manifest as validate_event_manifest
    from validate_memory_library_manifest import validate_manifest as validate_memory_manifest
    from validate_orphan_runtime_state_manifest import validate_manifest as validate_orphan_manifest
    from validate_queue_boundary_manifest import validate_manifest as validate_queue_manifest
    from validate_runtime_trace_manifest import validate_manifest as validate_runtime_trace_manifest

GENERIC_P0_DECISIONS = {
    "archive_candidate",
    "archive_candidate_after_caller_update",
    "keep_until_event_boundary_is_defined",
    "manual_review",
    "migrate_candidate",
    "migrate_candidate_after_caller_update",
    "orphan_runtime_state_review",
}


def build_boundary_readiness_audit(
    repo_root: Path = PROJECT_ROOT,
    *,
    app_root: Path = APP_ROOT,
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    app = Path(app_root).resolve()

    manifests = [
        _manifest_summary("memory_library_manifest", validate_memory_manifest()),
        _manifest_summary("event_boundary_manifest", validate_event_manifest(app / "stores/event_boundary_manifest.json")),
        _manifest_summary("runtime_trace_manifest", validate_runtime_trace_manifest(app / "stores/runtime_trace_manifest.json")),
        _manifest_summary("queue_boundary_manifest", validate_queue_manifest(app / "stores/queue_boundary_manifest.json")),
        _manifest_summary("orphan_runtime_state_manifest", validate_orphan_manifest(app / "stores/orphan_runtime_state_manifest.json")),
    ]

    reference_audits = [
        _reference_audit_summary("event_log_boundary_audit", build_event_log_boundary_audit(app)),
        _reference_audit_summary("runtime_trace_boundary_audit", build_runtime_trace_boundary_audit(app)),
        _reference_audit_summary("queue_boundary_audit", build_queue_boundary_audit(app)),
    ]
    orphan_audit = build_orphan_runtime_state_audit(repo)
    p0 = build_p0_triage(repo)
    p0_summary = _p0_summary(p0)

    manifest_failure_count = sum(1 for item in manifests if not item["ok"])
    reference_failure_count = sum(1 for item in reference_audits if item["status"] != "pass")
    generic_decision_count = p0_summary["generic_decision_count"]
    status = "pass"
    if manifest_failure_count or reference_failure_count:
        status = "fail"
    elif generic_decision_count:
        status = "hold"

    return {
        "status": status,
        "manifest_count": len(manifests),
        "manifest_failure_count": manifest_failure_count,
        "reference_audit_count": len(reference_audits),
        "reference_failure_count": reference_failure_count,
        "manifests": manifests,
        "reference_audits": reference_audits,
        "orphan_runtime_state_audit": {
            "status": orphan_audit.get("status", ""),
            "orphan_candidate_count": orphan_audit.get("orphan_candidate_count", 0),
            "held_orphan_count": orphan_audit.get("held_orphan_count", 0),
        },
        "p0": p0_summary,
        "privacy_note": (
            "Aggregates manifest metadata, source path references, and P0 decisions only; "
            "does not read or print JSON/JSONL bodies, raw QQ payloads, tokens, or private memory bodies."
        ),
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# XinYu Boundary Readiness Audit",
        "",
        "This report aggregates existing boundary manifests, source-reference audits, and P0 structured-memory decisions.",
        "It does not read or print JSON/JSONL bodies, raw QQ payloads, tokens, or private memory bodies.",
        "",
        f"- status: {audit['status']}",
        f"- manifest_count: {audit['manifest_count']}",
        f"- manifest_failure_count: {audit['manifest_failure_count']}",
        f"- reference_audit_count: {audit['reference_audit_count']}",
        f"- reference_failure_count: {audit['reference_failure_count']}",
        f"- p0_generic_decision_count: {audit['p0']['generic_decision_count']}",
        "",
        "## Manifests",
        "",
    ]
    for item in audit.get("manifests") or []:
        lines.append(
            f"- `{item['manifest_id']}` | ok={item['ok']} | checks={item['check_count']} | "
            f"failures={item['failure_count']} | warnings={item['warning_count']}"
        )
        for failure in item.get("failures") or []:
            lines.append(f"  - failure: {failure}")

    lines.extend(["", "## Reference Audits", ""])
    for item in audit.get("reference_audits") or []:
        lines.append(
            f"- `{item['audit_id']}` | status={item['status']} | items={item['item_count']} | "
            f"undeclared={item['undeclared_reference_count']}"
        )

    orphan = audit.get("orphan_runtime_state_audit") or {}
    lines.extend(
        [
            "",
            "## Orphan Runtime State",
            "",
            f"- status: {orphan.get('status', '')}",
            f"- orphan_candidate_count: {orphan.get('orphan_candidate_count', 0)}",
            f"- held_orphan_count: {orphan.get('held_orphan_count', 0)}",
            "",
            "## P0 Decisions",
            "",
        ]
    )
    p0 = audit.get("p0") or {}
    by_decision = p0.get("by_initial_decision") or {}
    if by_decision:
        for decision, count in sorted(by_decision.items()):
            lines.append(f"- {decision}: {count}")
    else:
        lines.append("- none")
    remaining = p0.get("generic_decisions") or {}
    if remaining:
        lines.extend(["", "## Remaining Generic Decisions", ""])
        for decision, count in sorted(remaining.items()):
            lines.append(f"- {decision}: {count}")
    return "\n".join(lines).rstrip() + "\n"


def generic_decision_count(by_initial_decision: dict[str, Any]) -> int:
    count = 0
    for decision, value in by_initial_decision.items():
        if str(decision) in GENERIC_P0_DECISIONS:
            try:
                count += int(value)
            except (TypeError, ValueError):
                count += 1
    return count


def _p0_summary(p0: dict[str, Any]) -> dict[str, Any]:
    by_initial_decision = dict(p0.get("by_initial_decision") or {})
    generic = {
        decision: count
        for decision, count in by_initial_decision.items()
        if str(decision) in GENERIC_P0_DECISIONS
    }
    return {
        "total_p0_items": p0.get("total_p0_items", 0),
        "by_initial_decision": by_initial_decision,
        "generic_decisions": generic,
        "generic_decision_count": generic_decision_count(by_initial_decision),
    }


def _manifest_summary(manifest_id: str, result: Any) -> dict[str, Any]:
    failures = list(getattr(result, "failures", ()) or ())
    warnings = list(getattr(result, "warnings", ()) or ())
    checks = list(getattr(result, "checks", ()) or ())
    return {
        "manifest_id": manifest_id,
        "ok": bool(getattr(result, "ok", False)),
        "check_count": len(checks),
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "failures": failures,
        "warnings": warnings,
    }


def _reference_audit_summary(audit_id: str, audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit_id": audit_id,
        "status": audit.get("status", ""),
        "item_count": len(audit.get("items") or []),
        "undeclared_reference_count": audit.get("undeclared_reference_count", 0),
        "validation_failures": list(audit.get("validation_failures") or []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate XinYu boundary readiness without reading private bodies.")
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--app-root", type=Path, default=APP_ROOT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    audit = build_boundary_readiness_audit(args.repo_root, app_root=args.app_root)
    output = json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) if args.json else render_markdown(audit)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)
    return 0 if audit["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
