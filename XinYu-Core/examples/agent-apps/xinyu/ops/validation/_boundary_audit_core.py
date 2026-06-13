"""Shared engine for the event/queue/runtime-trace boundary audits.

The three boundary audits scan source-file path references against a manifest
declaration of `allowed_raw_readers`. They were near-identical copies that drifted
in a few places (normalize rule, reference ordering, skip set, scanned suffixes,
self-ignore list, and the manifest/field names). This module keeps the single
scanning engine here and expresses every per-audit difference as a small config,
so each audit's observable behavior is preserved exactly.

Privacy: scans source file paths and string references only. It never reads or
prints JSONL/queue bodies, raw QQ payloads, tokens, or private memory bodies.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# Directory parts shared by every boundary audit's scan-skip set.
BASE_SKIP_PARTS = frozenset(
    {
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
        "worklog",
        "_tmp_xinyu_probe",
    }
)

DECISION_HOLD = "hold_undeclared_raw_reader"
_APP_PREFIX = "XinYu-Core/examples/agent-apps/xinyu/"


@dataclass(frozen=True)
class BoundaryAuditConfig:
    """Describes the one boundary audit variant the shared engine should run."""

    # Manifest / output shape.
    manifest_key: str            # top-level list key, e.g. "streams"
    item_id_field: str           # per-item id field, e.g. "stream_id"
    count_field: str             # summary count field, e.g. "stream_count"
    decision_pass: str           # pass decision string for this variant
    default_manifest_name: str   # filename under stores/
    body_label: str              # private-body phrase used in privacy notes
    title: str                   # markdown report title

    # Scan behavior (the drifted bits, preserved per variant).
    source_suffixes: frozenset[str]
    skip_parts: frozenset[str]
    skip_ops_archive: bool       # whether to prune ops/archive/* subtrees
    normalize_mode: str          # "strip_app_prefix" | "lstrip_dotslash"
    find_mode: str               # "early_break" | "full_sorted"
    ignored_suffixes: tuple[str, ...]

    # Manifest loader/validator (imported from the matching validate_* module).
    validate_manifest: Callable[[Path], Any]
    load_manifest: Callable[[Path], dict[str, Any]]


def build_boundary_audit(
    app_root: Path,
    config: BoundaryAuditConfig,
    *,
    manifest_path: Path | None = None,
    max_examples: int = 8,
) -> dict[str, Any]:
    app = app_root.resolve()
    manifest_path = manifest_path or app / "stores" / config.default_manifest_name
    validation = config.validate_manifest(manifest_path)
    manifest = config.load_manifest(manifest_path) if manifest_path.exists() else {config.manifest_key: []}
    reference_index = _build_reference_index(app, config)
    items: list[dict[str, Any]] = []
    total_violations = 0

    for entry in manifest.get(config.manifest_key) or []:
        if not isinstance(entry, dict):
            continue
        path_value = _safe_str(entry.get("path"))
        allowed = {_normalize(item, config.normalize_mode) for item in entry.get("allowed_raw_readers") or []}
        references = _find_references(reference_index, path_value, config, max_examples=max_examples)
        undeclared = [
            ref
            for ref in references
            if _normalize(ref, config.normalize_mode) not in allowed and not _is_ignored(ref, config)
        ]
        total_violations += len(undeclared)
        items.append(
            {
                config.item_id_field: _safe_str(entry.get(config.item_id_field)),
                "path": path_value,
                "owner_module": _safe_str(entry.get("owner_module")),
                "allowed_raw_readers": sorted(allowed),
                "reference_count": len(references),
                "reference_examples": references[:max_examples],
                "undeclared_reference_count": len(undeclared),
                "undeclared_reference_examples": undeclared[:max_examples],
                "decision": config.decision_pass if not undeclared else DECISION_HOLD,
            }
        )

    return {
        "status": "pass" if validation.ok and total_violations == 0 else "fail",
        "manifest_ok": validation.ok,
        "validation_failures": list(validation.failures),
        "validation_warnings": list(validation.warnings),
        config.count_field: len(items),
        "undeclared_reference_count": total_violations,
        "items": items,
        "privacy_note": (
            "Scans source file paths and string references only; does not read "
            f"{config.body_label}, raw QQ payloads, tokens, or private memory bodies."
        ),
    }


def render_markdown(audit: dict[str, Any], config: BoundaryAuditConfig) -> str:
    item_label = config.item_id_field[:-3] if config.item_id_field.endswith("_id") else config.item_id_field
    section = config.manifest_key.capitalize()
    lines = [
        f"# {config.title}",
        "",
        f"This report scans source path references against `stores/{config.default_manifest_name}`.",
        f"It does not read or print {config.body_label}, raw QQ payloads, tokens, or private memory bodies.",
        "",
        f"- status: {audit['status']}",
        f"- manifest_ok: {audit['manifest_ok']}",
        f"- {config.count_field}: {audit[config.count_field]}",
        f"- undeclared_reference_count: {audit['undeclared_reference_count']}",
        "",
    ]
    failures = audit.get("validation_failures") or []
    if failures:
        lines.extend(["## Validation Failures", ""])
        for failure in failures:
            lines.append(f"- {failure}")
        lines.append("")
    lines.extend([f"## {section}", ""])
    for item in audit.get("items") or []:
        lines.append(
            f"- `{item['path']}` | {item_label}={item.get(config.item_id_field, '')} | decision={item['decision']} | "
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


def _build_reference_index(app_root: Path, config: BoundaryAuditConfig) -> list[tuple[str, str]]:
    index: list[tuple[str, str]] = []
    for rel, path in _iter_scannable_files(app_root, config):
        if path.suffix.lower() not in config.source_suffixes:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        index.append((rel, text))
    return index


def _iter_scannable_files(app_root: Path, config: BoundaryAuditConfig) -> list[tuple[str, Path]]:
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
            if _skip_parts(parts, config):
                continue
            if path.is_dir():
                pending.append(path)
            else:
                files.append((rel, path))
    return files


def _skip_parts(parts: tuple[str, ...], config: BoundaryAuditConfig) -> bool:
    if config.skip_ops_archive and len(parts) >= 2 and parts[:2] == ("ops", "archive"):
        return True
    if any(part in config.skip_parts for part in parts):
        return True
    return bool(parts) and parts[0] == "tests"


def _find_references(
    reference_index: list[tuple[str, str]],
    path_value: str,
    config: BoundaryAuditConfig,
    *,
    max_examples: int,
) -> list[str]:
    if not path_value:
        return []
    needles = {path_value, Path(path_value).name}
    refs: list[str] = []
    for rel, text in reference_index:
        if _is_ignored(rel, config):
            continue
        if any(needle and needle in text for needle in needles):
            refs.append(rel)
            if config.find_mode == "early_break" and len(refs) >= max_examples:
                break
    if config.find_mode == "early_break":
        return refs
    return sorted(dict.fromkeys(refs))[:max_examples]


def _is_ignored(rel: str, config: BoundaryAuditConfig) -> bool:
    normalized = rel.replace("\\", "/")
    return normalized.endswith(config.ignored_suffixes)


def _normalize(value: Any, mode: str) -> str:
    text = _safe_str(value).replace("\\", "/")
    if mode == "strip_app_prefix":
        if text.startswith(_APP_PREFIX):
            text = text[len(_APP_PREFIX):]
        return text
    return text.lstrip("./")


def _safe_str(value: Any) -> str:
    return str(value or "").strip()
