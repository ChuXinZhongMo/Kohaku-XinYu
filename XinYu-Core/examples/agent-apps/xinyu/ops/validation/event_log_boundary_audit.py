from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from ._boundary_audit_core import BASE_SKIP_PARTS, BoundaryAuditConfig, build_boundary_audit
    from ._boundary_audit_core import render_markdown as _render_markdown
    from ._validation_paths import ensure_validation_paths
    from .validate_event_boundary_manifest import DEFAULT_MANIFEST, load_manifest, validate_manifest
except ImportError:  # pragma: no cover - direct script execution
    from _boundary_audit_core import BASE_SKIP_PARTS, BoundaryAuditConfig, build_boundary_audit
    from _boundary_audit_core import render_markdown as _render_markdown
    from _validation_paths import ensure_validation_paths
    from validate_event_boundary_manifest import DEFAULT_MANIFEST, load_manifest, validate_manifest


APP_ROOT = ensure_validation_paths()

CONFIG = BoundaryAuditConfig(
    manifest_key="streams",
    item_id_field="stream_id",
    count_field="stream_count",
    decision_pass="pass_declared_boundary",
    default_manifest_name="event_boundary_manifest.json",
    body_label="JSONL event bodies",
    title="XinYu Event Log Boundary Audit",
    source_suffixes=frozenset({".py", ".ps1", ".ts", ".tsx", ".js", ".json", ".md", ".yaml", ".yml"}),
    skip_parts=BASE_SKIP_PARTS,
    skip_ops_archive=False,
    normalize_mode="strip_app_prefix",
    find_mode="early_break",
    ignored_suffixes=(
        "stores/event_boundary_manifest.json",
        "ops/validation/event_log_boundary_audit.py",
        "ops/validation/validate_event_boundary_manifest.py",
        "ops/validation/memory_structured_p0_triage.py",
    ),
    validate_manifest=validate_manifest,
    load_manifest=load_manifest,
)


def build_event_log_boundary_audit(
    app_root: Path = APP_ROOT,
    *,
    manifest_path: Path | None = None,
    max_examples: int = 8,
) -> dict[str, Any]:
    return build_boundary_audit(app_root, CONFIG, manifest_path=manifest_path, max_examples=max_examples)


def render_markdown(audit: dict[str, Any]) -> str:
    return _render_markdown(audit, CONFIG)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit event-log raw readers against the event boundary manifest.")
    parser.add_argument("--app-root", type=Path, default=APP_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args(argv)
    audit = build_event_log_boundary_audit(args.app_root, manifest_path=args.manifest)
    rendered = json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n" if args.json else render_markdown(audit)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if audit["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
