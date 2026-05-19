from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from ._validation_paths import ensure_validation_paths
except ImportError:  # pragma: no cover - direct script execution
    from _validation_paths import ensure_validation_paths


APP_ROOT = ensure_validation_paths("ops/validation")

try:
    from .memory_structured_p0_triage import build_p0_triage
    from .validate_orphan_runtime_state_manifest import DEFAULT_MANIFEST, held_state_paths, load_manifest
except ImportError:  # pragma: no cover - direct script execution
    from memory_structured_p0_triage import build_p0_triage
    from validate_orphan_runtime_state_manifest import DEFAULT_MANIFEST, held_state_paths, load_manifest


def build_orphan_runtime_state_audit(repo_root: Path) -> dict[str, Any]:
    triage = build_p0_triage(repo_root)
    held_paths = held_state_paths(DEFAULT_MANIFEST)
    hold_details = _hold_details_by_path(DEFAULT_MANIFEST)
    items: list[dict[str, Any]] = []
    for item in triage.get("items") or []:
        if not isinstance(item, dict):
            continue
        if item.get("category") != "durable_runtime_state":
            continue
        path = str(item.get("path", ""))
        app_rel = _app_rel(path)
        if item.get("initial_decision") == "held_orphan_runtime_state" or app_rel in held_paths:
            detail = hold_details.get(app_rel, {})
            items.append(
                {
                    "path": path,
                    "decision": "held_orphan_runtime_state",
                    "target_boundary": "stores/orphan_runtime_state_manifest",
                    "reference_count": 0,
                    "delete_allowed": False,
                    "handling": detail.get("handling")
                    or "Zero live source reference found; explicit hold remains until owner/archive review.",
                }
            )
            continue
        if item.get("reference_count") != 0:
            continue
        if item.get("initial_decision") == "migrate_candidate":
            items.append(
                {
                    "path": path,
                    "decision": "orphan_runtime_state_review",
                    "target_boundary": item.get("target_boundary", "stores/runtime_state"),
                    "reference_count": 0,
                    "delete_allowed": False,
                    "handling": "No live source reference found by the privacy-safe index; keep in place until an owner/archive decision is reviewed.",
                }
            )
    items.sort(key=lambda row: str(row["path"]))
    return {
        "status": "review",
        "orphan_candidate_count": len(items),
        "held_orphan_count": sum(1 for item in items if item.get("decision") == "held_orphan_runtime_state"),
        "items": items,
        "safety_rule": "This is a non-destructive review report. Do not delete, move, or print state bodies from this output alone.",
        "privacy_note": "Generated from P0 triage paths and source-code reference file names only; does not read JSON bodies, raw QQ payloads, tokens, or private memory bodies.",
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# XinYu Orphan Runtime State Audit",
        "",
        "This report lists durable runtime state JSON files with zero live source references in the P0 triage index.",
        "It does not read or print JSON bodies, raw QQ payloads, tokens, or private memory bodies.",
        "",
        f"- status: {audit['status']}",
        f"- orphan_candidate_count: {audit['orphan_candidate_count']}",
        f"- held_orphan_count: {audit.get('held_orphan_count', 0)}",
        "",
        "## Items",
        "",
    ]
    items = audit.get("items") or []
    if not items:
        lines.append("- none")
    else:
        for item in items:
            lines.append(
                f"- `{item['path']}` | decision={item['decision']} | "
                f"target={item['target_boundary']} | delete_allowed={item['delete_allowed']}"
            )
            lines.append(f"  - handling: {item['handling']}")
    lines.extend(
        [
            "",
            "## Safety Rule",
            "",
            f"- {audit['safety_rule']}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit zero-reference durable runtime state files without reading bodies.")
    parser.add_argument("--repo-root", default="D:\\XinYu")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default="")
    return parser


def _hold_details_by_path(path: Path) -> dict[str, dict[str, Any]]:
    try:
        manifest = load_manifest(path)
    except OSError:
        return {}
    result: dict[str, dict[str, Any]] = {}
    for state in manifest.get("states") or []:
        if isinstance(state, dict):
            text = str(state.get("path") or "").strip()
            if text:
                result[text] = state
    return result


def _app_rel(path: str) -> str:
    marker = "XinYu-Core/examples/agent-apps/xinyu/"
    normalized = path.replace("\\", "/")
    if marker in normalized:
        return normalized.split(marker, 1)[1]
    return normalized


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args(argv)
    audit = build_orphan_runtime_state_audit(Path(args.repo_root))
    rendered = json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n" if args.json else render_markdown(audit)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
