from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from ._validation_paths import ensure_validation_paths
except ImportError:  # pragma: no cover - direct script execution
    from _validation_paths import ensure_validation_paths


APP_ROOT = ensure_validation_paths()
PROJECT_ROOT = APP_ROOT.parents[3]
DEFAULT_MANIFEST = APP_ROOT / "stores" / "memory_library_manifest.json"

REQUIRED_FIELDS: tuple[str, ...] = (
    "path",
    "category",
    "tier",
    "include_policy",
    "sensitivity",
    "source_type",
    "license_or_consent",
    "retention_days",
    "contains_pii",
    "requires_redaction",
    "max_file_count",
    "snapshot_allowed",
    "last_verified_at",
    "verifier_version",
)

VALID_CATEGORIES = {"memory", "library", "cases", "data", "learning", "runtime"}
VALID_POLICIES = {"include", "exclude", "redact"}
VALID_SENSITIVITY = {"low", "medium", "high"}

SENSITIVE_DENY_PARTS: tuple[str, ...] = (
    "logs",
    "__pycache__",
    ".venv",
    ".pytest_cache",
    "pytest-tmp",
    "pytest_tmp",
    "codex-pytest",
    "codex_pytest",
    "codex-pytest-basetemp",
    "ad_shadow",
    "ad_log_shadow",
    "answer_discipline_trial_workspace",
    "debug-shadow-dir",
    "initiative_research_shadow_workspace",
    "dialogue_archive",
    "dialogue_working_memory",
    "group_shadow",
    "memory_repair_backup",
)


@dataclass(frozen=True, slots=True)
class ManifestCheck:
    path: str
    resolved: str
    exists: bool
    include_policy: str
    sensitivity: str
    file_count: int | None
    status: str
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ManifestValidationResult:
    checks: tuple[ManifestCheck, ...]
    failures: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.failures


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_manifest(path: Path = DEFAULT_MANIFEST) -> ManifestValidationResult:
    manifest = load_manifest(path)
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return ManifestValidationResult(
            checks=(),
            failures=("manifest entries must be a list",),
            warnings=(),
        )
    return validate_entries(entries)


def validate_entries(entries: list[Any]) -> ManifestValidationResult:
    checks: list[ManifestCheck] = []
    failures: list[str] = []
    warnings: list[str] = []
    seen_paths: set[str] = set()

    for index, raw in enumerate(entries, start=1):
        label = f"entry[{index}]"
        if not isinstance(raw, dict):
            failures.append(f"{label}: entry must be an object")
            continue
        entry = raw
        path_value = _safe_str(entry.get("path"))
        label = path_value or label
        missing = [field for field in REQUIRED_FIELDS if field not in entry]
        if missing:
            failures.append(f"{label}: missing fields: {', '.join(missing)}")
            continue
        if path_value in seen_paths:
            failures.append(f"{label}: duplicate path")
        seen_paths.add(path_value)

        category = _safe_str(entry.get("category"))
        policy = _safe_str(entry.get("include_policy"))
        sensitivity = _safe_str(entry.get("sensitivity"))
        if category not in VALID_CATEGORIES:
            failures.append(f"{label}: invalid category {category!r}")
        if policy not in VALID_POLICIES:
            failures.append(f"{label}: invalid include_policy {policy!r}")
        if sensitivity not in VALID_SENSITIVITY:
            failures.append(f"{label}: invalid sensitivity {sensitivity!r}")

        resolved = resolve_manifest_path(path_value)
        if resolved is None:
            failures.append(f"{label}: path is outside the app/project boundary")
            continue

        denylisted = is_sensitive_deny_path(path_value)
        snapshot_allowed = bool(entry.get("snapshot_allowed"))
        requires_redaction = bool(entry.get("requires_redaction"))
        contains_pii = bool(entry.get("contains_pii"))
        notes: list[str] = []

        if denylisted and policy == "include":
            failures.append(f"{label}: denylisted path cannot be directly included")
        if denylisted and snapshot_allowed:
            failures.append(f"{label}: denylisted path cannot allow snapshots")
        if sensitivity == "high" and policy == "include" and not requires_redaction:
            failures.append(f"{label}: high-sensitivity include requires redaction")
        if contains_pii and snapshot_allowed:
            failures.append(f"{label}: PII paths cannot allow snapshots")
        if path_value.startswith("memory") and category not in {"memory", "library"}:
            failures.append(f"{label}: memory path has unexpected category {category!r}")
        if path_value.startswith("data/conversation_experience") and category != "cases":
            failures.append(f"{label}: conversation experience must be categorized as cases")
        if path_value.startswith("data/external") and category != "library":
            failures.append(f"{label}: external data must be categorized as library")

        exists = resolved.exists()
        if not exists:
            warnings.append(f"{label}: path missing")
            file_count = None
            notes.append("missing_expected_path")
        elif policy == "exclude":
            file_count = None
            notes.append("excluded_not_enumerated")
        else:
            max_file_count = _safe_int(entry.get("max_file_count"), default=0)
            file_count = count_files_bounded(resolved, max_files=max_file_count + 1)
            if max_file_count >= 0 and file_count > max_file_count:
                failures.append(f"{label}: file count {file_count} exceeds max_file_count {max_file_count}")

        checks.append(
            ManifestCheck(
                path=path_value,
                resolved=redacted_display_path(resolved),
                exists=exists,
                include_policy=policy,
                sensitivity=sensitivity,
                file_count=file_count,
                status="ok" if not denylisted else "sensitive_boundary",
                notes=tuple(notes),
            )
        )

    return ManifestValidationResult(
        checks=tuple(checks),
        failures=tuple(failures),
        warnings=tuple(warnings),
    )


def resolve_manifest_path(path_value: str) -> Path | None:
    if not path_value or Path(path_value).is_absolute():
        return None
    if path_value.startswith("project:"):
        suffix = path_value.removeprefix("project:").strip("/\\")
        resolved = (PROJECT_ROOT / suffix).resolve()
        if not _is_relative_to(resolved, PROJECT_ROOT):
            return None
        return resolved
    resolved = (APP_ROOT / path_value).resolve()
    if not _is_relative_to(resolved, APP_ROOT):
        return None
    return resolved


def is_sensitive_deny_path(path_value: str) -> bool:
    parts = tuple(part.lower() for part in path_value.replace("\\", "/").split("/") if part)
    compact = "/".join(parts)
    return any(needle in compact or needle in parts for needle in SENSITIVE_DENY_PARTS)


def count_files_bounded(path: Path, *, max_files: int) -> int:
    if path.is_file():
        return 1
    if not path.exists():
        return 0
    count = 0
    for child in path.rglob("*"):
        if child.is_file():
            count += 1
            if max_files > 0 and count >= max_files:
                return count
    return count


def redacted_display_path(path: Path) -> str:
    try:
        return str(path.relative_to(APP_ROOT)).replace("\\", "/")
    except ValueError:
        try:
            return "project:" + str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        except ValueError:
            return "[outside-project]"


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _result_payload(result: ManifestValidationResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "failures": list(result.failures),
        "warnings": list(result.warnings),
        "checks": [
            {
                "path": check.path,
                "resolved": check.resolved,
                "exists": check.exists,
                "include_policy": check.include_policy,
                "sensitivity": check.sensitivity,
                "file_count": check.file_count,
                "status": check.status,
                "notes": list(check.notes),
            }
            for check in result.checks
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate XinYu memory/library manifest metadata without reading contents.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true", help="Print redacted JSON result.")
    args = parser.parse_args(argv)

    result = validate_manifest(args.manifest)
    if args.json:
        print(json.dumps(_result_payload(result), ensure_ascii=False, indent=2, sort_keys=True))
    elif result.ok:
        print("Memory/library manifest validation passed")
        for check in result.checks:
            count = "excluded" if check.file_count is None else str(check.file_count)
            print(f"- {check.path}: {check.include_policy}, {check.sensitivity}, files={count}")
    else:
        print("Memory/library manifest validation failed")
        for failure in result.failures:
            print(f"- {failure}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
