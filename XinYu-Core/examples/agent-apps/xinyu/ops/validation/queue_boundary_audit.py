from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from ._validation_paths import ensure_validation_paths
    from .validate_queue_boundary_manifest import DEFAULT_MANIFEST, load_manifest, validate_manifest
except ImportError:  # pragma: no cover - direct script execution
    from _validation_paths import ensure_validation_paths
    from validate_queue_boundary_manifest import DEFAULT_MANIFEST, load_manifest, validate_manifest


APP_ROOT = ensure_validation_paths()
SOURCE_SUFFIXES = {".py", ".ps1", ".ts", ".tsx", ".js", ".json", ".yaml", ".yml"}
SKIP_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "memory",
    "runtime",
    "data",
    "library",
    "cases",
    "logs",
    "project-plans",
}
IGNORED_REFERENCE_SUFFIXES = (
    "stores/queue_boundary_manifest.json",
    "ops/validation/queue_boundary_audit.py",
    "ops/validation/validate_queue_boundary_manifest.py",
    "ops/validation/memory_structured_p0_triage.py",
    "ops/validation/timestamp_invalid_schema_classifier.py",
)


def build_queue_boundary_audit(
    app_root: Path = APP_ROOT,
    *,
    manifest_path: Path | None = None,
    max_examples: int = 8,
) -> dict[str, Any]:
    app = app_root.resolve()
    manifest_path = manifest_path or app / "stores" / "queue_boundary_manifest.json"
    validation = validate_manifest(manifest_path)
    manifest = load_manifest(manifest_path) if manifest_path.exists() else {"queues": []}
    reference_index = _build_reference_index(app)
    items: list[dict[str, Any]] = []
    total_violations = 0

    for queue in manifest.get("queues") or []:
        if not isinstance(queue, dict):
            continue
        path_value = _safe_str(queue.get("path"))
        allowed = {_normalize_source_path(item) for item in queue.get("allowed_raw_readers") or []}
        references = _find_references(reference_index, path_value, max_examples=max_examples)
        undeclared = [
            ref
            for ref in references
            if _normalize_source_path(ref) not in allowed and not _is_ignored_reference(ref)
        ]
        total_violations += len(undeclared)
        items.append(
            {
                "queue_id": _safe_str(queue.get("queue_id")),
                "path": path_value,
                "owner_module": _safe_str(queue.get("owner_module")),
                "allowed_raw_readers": sorted(allowed),
                "reference_count": len(references),
                "reference_examples": references[:max_examples],
                "undeclared_reference_count": len(undeclared),
                "undeclared_reference_examples": undeclared[:max_examples],
                "decision": "pass_declared_queue_boundary" if not undeclared else "hold_undeclared_raw_reader",
            }
        )

    return {
        "status": "pass" if validation.ok and total_violations == 0 else "fail",
        "manifest_ok": validation.ok,
        "validation_failures": list(validation.failures),
        "validation_warnings": list(validation.warnings),
        "queue_count": len(items),
        "undeclared_reference_count": total_violations,
        "items": items,
        "privacy_note": "Scans source file paths and string references only; does not read queue bodies, raw QQ payloads, tokens, or private memory bodies.",
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# XinYu Queue Boundary Audit",
        "",
        "This report scans source path references against `stores/queue_boundary_manifest.json`.",
        "It does not read or print queue bodies, raw QQ payloads, tokens, or private memory bodies.",
        "",
        f"- status: {audit['status']}",
        f"- manifest_ok: {audit['manifest_ok']}",
        f"- queue_count: {audit['queue_count']}",
        f"- undeclared_reference_count: {audit['undeclared_reference_count']}",
        "",
    ]
    failures = audit.get("validation_failures") or []
    if failures:
        lines.extend(["## Validation Failures", ""])
        for failure in failures:
            lines.append(f"- {failure}")
        lines.append("")
    lines.extend(["## Queues", ""])
    for item in audit.get("items") or []:
        lines.append(
            f"- `{item['path']}` | queue={item['queue_id']} | decision={item['decision']} | "
            f"refs={item['reference_count']} | undeclared={item['undeclared_reference_count']}"
        )
        if item.get("reference_examples"):
            lines.append("  - reference_examples:")
            for example in item["reference_examples"]:
                lines.append(f"    - `{example}`")
        if item.get("undeclared_reference_examples"):
            lines.append("  - undeclared_reference_examples:")
            for example in item["undeclared_reference_examples"]:
                lines.append(f"    - `{example}`")
    return "\n".join(lines).rstrip() + "\n"


def _build_reference_index(app_root: Path) -> list[tuple[str, str]]:
    index: list[tuple[str, str]] = []
    for rel, path in _iter_scannable_files(app_root):
        if path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        index.append((rel, text))
    return index


def _iter_scannable_files(app_root: Path) -> list[tuple[str, Path]]:
    if not app_root.exists():
        return []
    files: list[tuple[str, Path]] = []
    pending = [app_root]
    while pending:
        current = pending.pop()
        try:
            children = sorted(current.iterdir(), key=lambda item: item.as_posix().lower())
        except OSError:
            continue
        for path in children:
            rel = path.relative_to(app_root).as_posix()
            parts = tuple(part.lower() for part in Path(rel).parts)
            if path.is_dir():
                if _skip_rel(parts):
                    continue
                if any(part in SKIP_PARTS for part in parts):
                    continue
                if parts and parts[0] == "tests":
                    continue
                pending.append(path)
                continue
            if _skip_rel(parts):
                continue
            if any(part in SKIP_PARTS for part in parts):
                continue
            if parts and parts[0] == "tests":
                continue
            files.append((rel, path))
    return files


def _find_references(reference_index: list[tuple[str, str]], path_value: str, *, max_examples: int) -> list[str]:
    if not path_value:
        return []
    name = Path(path_value).name
    needles = {path_value, name}
    refs: list[str] = []
    for rel, text in reference_index:
        if _is_ignored_reference(rel):
            continue
        if any(needle and needle in text for needle in needles):
            refs.append(rel)
    return sorted(dict.fromkeys(refs))[:max_examples]


def _normalize_source_path(value: str) -> str:
    return value.replace("\\", "/").lstrip("./")


def _is_ignored_reference(value: str) -> bool:
    normalized = _normalize_source_path(value)
    return any(normalized.endswith(suffix) for suffix in IGNORED_REFERENCE_SUFFIXES)


def _skip_rel(parts: tuple[str, ...]) -> bool:
    return len(parts) >= 2 and parts[:2] == ("ops", "archive")


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


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
