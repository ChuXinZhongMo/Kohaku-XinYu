from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from ._boundary_audit_core import BASE_SKIP_PARTS, BoundaryAuditConfig, build_boundary_audit
    from ._boundary_audit_core import render_markdown as _render_markdown
    from ._validation_paths import ensure_validation_paths
    from .validate_queue_boundary_manifest import load_manifest, validate_manifest
except ImportError:  # pragma: no cover - direct script execution
    from _boundary_audit_core import BASE_SKIP_PARTS, BoundaryAuditConfig, build_boundary_audit
    from _boundary_audit_core import render_markdown as _render_markdown
    from _validation_paths import ensure_validation_paths
    from validate_queue_boundary_manifest import load_manifest, validate_manifest


APP_ROOT = ensure_validation_paths()

CONFIG = BoundaryAuditConfig(
    manifest_key="queues",
    item_id_field="queue_id",
    count_field="queue_count",
    decision_pass="pass_declared_queue_boundary",
    default_manifest_name="queue_boundary_manifest.json",
    body_label="queue bodies",
    title="XinYu Queue Boundary Audit",
    source_suffixes=frozenset({".py", ".ps1", ".ts", ".tsx", ".js", ".json", ".yaml", ".yml"}),
    skip_parts=BASE_SKIP_PARTS | {"project-plans"},
    skip_ops_archive=True,
    normalize_mode="lstrip_dotslash",
    find_mode="full_sorted",
    ignored_suffixes=(
        "stores/queue_boundary_manifest.json",
        "ops/validation/queue_boundary_audit.py",
        "ops/validation/validate_queue_boundary_manifest.py",
        "ops/validation/memory_structured_p0_triage.py",
        "ops/validation/timestamp_invalid_schema_classifier.py",
    ),
    validate_manifest=validate_manifest,
    load_manifest=load_manifest,
)


def build_queue_boundary_audit(
    app_root: Path = APP_ROOT,
    *,
    manifest_path: Path | None = None,
    max_examples: int = 8,
) -> dict[str, Any]:
    return build_boundary_audit(app_root, CONFIG, manifest_path=manifest_path, max_examples=max_examples)


def render_markdown(audit: dict[str, Any]) -> str:
    return _render_markdown(audit, CONFIG)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit XinYu runtime queue boundary references.")
    parser.add_argument("--app-root", type=Path, default=APP_ROOT)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    audit = build_queue_boundary_audit(args.app_root, manifest_path=args.manifest)
    output = json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) if args.json else render_markdown(audit)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)
    return 0 if audit["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
