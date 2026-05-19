from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from ._validation_paths import ensure_validation_paths
except ImportError:  # pragma: no cover - direct script execution
    from _validation_paths import ensure_validation_paths


APP_ROOT = ensure_validation_paths("ops/validation")
PROJECT_ROOT = APP_ROOT.parents[3]
APP_REL = Path("XinYu-Core/examples/agent-apps/xinyu")
TEXT_SUFFIXES = {".md", ".json", ".jsonl", ".yaml", ".yml", ".txt"}
SKIP_DIR_NAMES = {".git", ".pytest_cache", "__pycache__", "pytest-tmp", "pytest_tmp", "codex_tmp"}
MAX_METADATA_FILE_BYTES = 2_000_000
MAX_JSONL_ROWS_PER_FILE = 200
TIMESTAMP_KEYS = (
    "event_time",
    "observed_at",
    "recorded_at",
    "created_at",
    "updated_at",
    "timestamp",
    "started_at",
    "last_seen_at",
)

from xinyu_bridge_state_text import payload_event_time_iso  # noqa: E402


@dataclass(frozen=True)
class TimestampFileRecord:
    path: str
    zone: str
    file_type: str
    inspected_rows: int
    timestamp_key_counts: dict[str, int]
    missing_count: int
    invalid_count: int

    @property
    def has_timestamp(self) -> bool:
        return any(self.timestamp_key_counts.values())


def build_timestamp_provenance_audit(repo_root: Path = PROJECT_ROOT, *, issue_limit: int = 160) -> dict[str, Any]:
    records = collect_timestamp_records(repo_root)
    return summarize(records, issue_limit=issue_limit)


def collect_timestamp_records(repo_root: Path) -> list[TimestampFileRecord]:
    repo = Path(repo_root).resolve()
    roots = (
        repo / APP_REL / "memory",
        repo / "cases",
        repo / "library",
        repo / APP_REL / "runtime",
        repo / APP_REL / "data",
    )
    records: list[TimestampFileRecord] = []
    for root in roots:
        if not root.exists():
            continue
        for path in iter_metadata_files(root):
            records.append(inspect_timestamp_file(repo, path))
    return records


def inspect_timestamp_file(repo_root: Path, path: Path) -> TimestampFileRecord:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return inspect_jsonl_file(repo_root, path)
    if suffix == ".json":
        return inspect_json_file(repo_root, path)
    if suffix == ".md":
        return inspect_markdown_file(repo_root, path)
    return TimestampFileRecord(
        path=rel_path(repo_root, path),
        zone=classify_zone(repo_root, path),
        file_type=suffix.lstrip(".") or "text",
        inspected_rows=0,
        timestamp_key_counts={},
        missing_count=0,
        invalid_count=0,
    )


def inspect_markdown_file(repo_root: Path, path: Path) -> TimestampFileRecord:
    fields = markdown_metadata_fields(path)
    key_counts: Counter[str] = Counter()
    invalid = 0
    for key, value in fields.items():
        if key not in TIMESTAMP_KEYS:
            continue
        key_counts[key] += 1
        if not is_valid_timestamp_value(key, value):
            invalid += 1
    return TimestampFileRecord(
        path=rel_path(repo_root, path),
        zone=classify_zone(repo_root, path),
        file_type="md",
        inspected_rows=1,
        timestamp_key_counts=dict(sorted(key_counts.items())),
        missing_count=0 if key_counts else 1,
        invalid_count=invalid,
    )


def inspect_json_file(repo_root: Path, path: Path) -> TimestampFileRecord:
    rows = list(iter_json_records(path, max_rows=MAX_JSONL_ROWS_PER_FILE))
    return record_for_rows(repo_root, path, "json", rows)


def inspect_jsonl_file(repo_root: Path, path: Path) -> TimestampFileRecord:
    rows = list(iter_jsonl_records(path, max_rows=MAX_JSONL_ROWS_PER_FILE))
    return record_for_rows(repo_root, path, "jsonl", rows)


def record_for_rows(repo_root: Path, path: Path, file_type: str, rows: list[dict[str, Any]]) -> TimestampFileRecord:
    key_counts: Counter[str] = Counter()
    missing = 0
    invalid = 0
    for row in rows:
        row_keys = [key for key in TIMESTAMP_KEYS if key in row]
        if not row_keys:
            missing += 1
            continue
        for key in row_keys:
            key_counts[key] += 1
            if not is_valid_timestamp_value(key, row.get(key)):
                invalid += 1
    return TimestampFileRecord(
        path=rel_path(repo_root, path),
        zone=classify_zone(repo_root, path),
        file_type=file_type,
        inspected_rows=len(rows),
        timestamp_key_counts=dict(sorted(key_counts.items())),
        missing_count=missing,
        invalid_count=invalid,
    )


def summarize(records: list[TimestampFileRecord], *, issue_limit: int = 160) -> dict[str, Any]:
    zone_counts = Counter(record.zone for record in records)
    file_type_counts = Counter(record.file_type for record in records)
    timestamp_key_counts: Counter[str] = Counter()
    for record in records:
        timestamp_key_counts.update(record.timestamp_key_counts)
    missing_files = [record for record in records if record.missing_count > 0]
    invalid_files = [record for record in records if record.invalid_count > 0]
    status = "pass" if not missing_files and not invalid_files else "hold"
    return {
        "status": status,
        "privacy_note": (
            "Metadata-only timestamp audit. Reports paths, zones, counts, and issue types only; "
            "does not print memory bodies, JSON/JSONL bodies, raw QQ payloads, tokens, or timestamp values."
        ),
        "total_files": len(records),
        "total_inspected_rows": sum(record.inspected_rows for record in records),
        "files_with_timestamp": sum(1 for record in records if record.has_timestamp),
        "files_missing_timestamp": len(missing_files),
        "files_with_invalid_timestamp": len(invalid_files),
        "missing_timestamp_count": sum(record.missing_count for record in records),
        "invalid_timestamp_count": sum(record.invalid_count for record in records),
        "zone_counts": dict(sorted(zone_counts.items())),
        "file_type_counts": dict(sorted(file_type_counts.items())),
        "timestamp_key_counts": dict(sorted(timestamp_key_counts.items())),
        "issue_limit": max(0, int(issue_limit)),
        "issues": [
            {
                "path": record.path,
                "zone": record.zone,
                "file_type": record.file_type,
                "inspected_rows": record.inspected_rows,
                "missing_count": record.missing_count,
                "invalid_count": record.invalid_count,
            }
            for record in [*missing_files, *invalid_files][: max(0, int(issue_limit))]
        ],
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# XinYu Timestamp Provenance Audit",
        "",
        audit["privacy_note"],
        "",
        f"- status: {audit['status']}",
        f"- total_files: {audit['total_files']}",
        f"- total_inspected_rows: {audit['total_inspected_rows']}",
        f"- files_with_timestamp: {audit['files_with_timestamp']}",
        f"- files_missing_timestamp: {audit['files_missing_timestamp']}",
        f"- files_with_invalid_timestamp: {audit['files_with_invalid_timestamp']}",
        f"- missing_timestamp_count: {audit['missing_timestamp_count']}",
        f"- invalid_timestamp_count: {audit['invalid_timestamp_count']}",
        "",
        "## Timestamp Keys",
        "",
    ]
    for key, count in (audit.get("timestamp_key_counts") or {}).items():
        lines.append(f"- {key}: {count}")
    if not audit.get("timestamp_key_counts"):
        lines.append("- none")
    lines.extend(["", "## Zone Counts", ""])
    for zone, count in (audit.get("zone_counts") or {}).items():
        lines.append(f"- {zone}: {count}")
    lines.extend(["", "## Review Items", ""])
    issues = audit.get("issues") or []
    if not issues:
        lines.append("- none")
    else:
        for item in issues:
            lines.append(
                f"- `{item['path']}` | zone={item['zone']} | type={item['file_type']} | "
                f"rows={item['inspected_rows']} | missing={item['missing_count']} | invalid={item['invalid_count']}"
            )
    return "\n".join(lines).rstrip() + "\n"


def markdown_metadata_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[:80]
    except OSError:
        return fields
    in_frontmatter = bool(lines and lines[0].strip() == "---")
    for line in lines[1:] if in_frontmatter else lines:
        stripped = line.strip()
        if in_frontmatter and stripped == "---":
            break
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        if key in TIMESTAMP_KEYS:
            fields[key] = value.strip()
    return fields


def iter_json_records(path: Path, *, max_rows: int) -> Iterable[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(data, dict):
        yield data
        return
    if isinstance(data, list):
        yielded = 0
        for item in data:
            if yielded >= max_rows:
                break
            if isinstance(item, dict):
                yielded += 1
                yield item


def iter_jsonl_records(path: Path, *, max_rows: int) -> Iterable[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return
    yielded = 0
    for line in lines:
        if yielded >= max_rows:
            break
        stripped = line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            yielded += 1
            yield data


def is_valid_timestamp_value(key: str, value: Any) -> bool:
    return bool(payload_event_time_iso({key: value}, fallback=""))


def classify_zone(repo_root: Path, path: Path) -> str:
    rel = rel_path(repo_root, path)
    app_prefix = APP_REL.as_posix() + "/"
    app_rel = rel[len(app_prefix) :] if rel.startswith(app_prefix) else rel
    if rel.startswith("cases/"):
        return "cases"
    if rel.startswith("library/"):
        return "library"
    if app_rel.startswith("memory/"):
        return "memory"
    if app_rel.startswith("runtime/"):
        return "runtime"
    if app_rel.startswith("data/"):
        return "legacy.data"
    return "unknown"


def iter_metadata_files(root: Path) -> Iterable[Path]:
    pending = [root]
    while pending:
        current = pending.pop()
        try:
            children = sorted(current.iterdir(), key=lambda item: item.as_posix().lower())
        except OSError:
            continue
        for path in children:
            if path.is_dir():
                if path.name in SKIP_DIR_NAMES:
                    continue
                pending.append(path)
                continue
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > MAX_METADATA_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield path


def rel_path(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(Path(repo_root).resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit timestamp metadata without printing memory bodies.")
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--issue-limit", type=int, default=160)
    args = parser.parse_args()
    audit = build_timestamp_provenance_audit(args.repo_root, issue_limit=args.issue_limit)
    output = json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) if args.json else render_markdown(audit)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
