from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

try:
    from ._validation_paths import ensure_validation_paths
except ImportError:  # pragma: no cover - direct script execution
    from _validation_paths import ensure_validation_paths


APP_ROOT = ensure_validation_paths("ops/validation")

SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js"}
SKIP_DIR_NAMES = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "data",
    "dist",
    "env",
    "logs",
    "memory",
    "node_modules",
    "ops",
    "project-plans",
    "runtime",
    "tests",
    "venv",
}
SKIP_DIR_PREFIXES = ("codex-",)
SKIP_REL_PATH_PREFIXES = (
    "learning/self_found",
)
MAX_SOURCE_FILE_BYTES = 1_000_000

TIMESTAMP_FIELDS = (
    "event_time",
    "observed_at",
    "recorded_at",
    "created_at",
    "updated_at",
    "timestamp",
    "started_at",
    "last_seen_at",
)
TIMESTAMP_FIELD_RE = re.compile(
    r"['\"]?(?P<field>\b(?:"
    + "|".join(re.escape(field) for field in TIMESTAMP_FIELDS)
    + r")\b)['\"]?\s*[:=]"
)
DEF_RE = re.compile(r"^\s*def\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")
TIMESTAMP_CONDITION_RE = re.compile(
    r"^\s*(?:if|elif)\s+(?:not\s+)?(?:"
    + "|".join(re.escape(field) for field in TIMESTAMP_FIELDS)
    + r")\s*:"
)
TIMESTAMP_AGE_CALCULATION_RE = re.compile(
    r"\b_age_seconds\([^)]*\b(?:"
    + "|".join(re.escape(field) for field in TIMESTAMP_FIELDS)
    + r")\s*="
)
RISKY_FALLBACK_RE = re.compile(
    r"(?i)(?:\bor\s+['\"](?:none|unknown|missing|null|n/a|na)?['\"]|"
    r"['\"](?:none|unknown|missing|null|n/a|na)['\"]\s*[}\)],?|"
    r"default\s*=\s*['\"](?:none|unknown|missing|null|n/a|na)?['\"]|"
    r"fallback\s*=\s*['\"](?:none|unknown|missing|null|n/a|na)?['\"]|"
    r"\bor\s+None\b)"
)
GUARD_TOKENS = (
    "_replacement_value(",
    "_timestamp_or_now_iso(",
    "_now_iso(",
    "_iso(",
    "datetime.now(",
    ".isoformat(",
    "now_iso(",
    "payload_event_time_iso(",
    "iso_from_timestamp(",
    "event_time_for(",
    "_event_time_for(",
)
REFERENCE_ONLY_LINE_TOKENS = (
    "parser.add_argument(",
    "_extract_field(",
)
SCHEMA_REFERENCE_TOKENS = (
    "SCHEMA",
    "TIMESTAMP_FIELDS",
    "_FIELD_RE",
    "_FRONTMATTER_FIELD_RE",
    ".get(",
    "field_counts",
    "fields.get(",
    "payload.get(",
    "metadata.get(",
    "row.get(",
    "row[",
    "state.get(",
    "timestamp_key_counts",
    "wanted",
    "excluded.",
    "= ?",
)
REPORT_METADATA_TOKENS = (
    "audit",
    "dashboard",
    "metrics",
    "report",
    "result",
    "summary",
)
REFERENCE_ONLY_SCOPE_NAMES = {
    "_default_fields",
    "_load_codex_fields",
}
DIRECT_STRING_FIELD_RE = re.compile(
    r"['\"]-?\s*(?:"
    + "|".join(re.escape(field) for field in TIMESTAMP_FIELDS)
    + r")\s*:"
)
TEMPLATE_FIELD_RE = re.compile(
    r"^\s*-?\s*(?:"
    + "|".join(re.escape(field) for field in TIMESTAMP_FIELDS)
    + r")\s*:"
)
WRITER_TOKENS = (
    ".write_text(",
    ".write(",
    "append_jsonl(",
    "atomic_write_json(",
    "atomic_write_text(",
    "json.dump(",
    "json.dumps(",
    "record_",
    "save_",
    "persist",
)
MONOTONIC_RUNTIME_TOKENS = (
    "time.monotonic()",
)


def build_timestamp_writer_guard_audit(app_root: Path = APP_ROOT) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    source_files = list(iter_source_files(app_root))
    for path in source_files:
        items.extend(scan_source_file(app_root, path))
    status_counts = Counter(item["guard_status"] for item in items)
    field_counts = Counter(item["field"] for item in items)
    line_kind_counts = Counter(item["line_kind"] for item in items)
    return {
        "status": "review" if status_counts.get("risky_literal_fallback") or status_counts.get("unguarded_candidate") else "pass",
        "source_file_count": len(source_files),
        "timestamp_writer_candidate_count": len(items),
        "guard_status_counts": dict(sorted(status_counts.items())),
        "field_counts": dict(sorted(field_counts.items())),
        "line_kind_counts": dict(sorted(line_kind_counts.items())),
        "items": sorted(items, key=lambda item: (item["guard_status"], item["path"], item["line"])),
        "privacy_note": (
            "Metadata-only source audit. Reports source file paths, line numbers, timestamp field names, "
            "and guard status only. It skips memory, runtime, data, tests, ops, logs, and generated folders; "
            "it does not read or print memory bodies, raw QQ payloads, timestamp values, tokens, secrets, "
            "or source-line text."
        ),
    }


def scan_source_file(app_root: Path, path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    rel = rel_to_root(app_root, path)
    writer_source = is_potential_writer_source(lines)
    items: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        match = TIMESTAMP_FIELD_RE.search(line)
        if not match:
            continue
        field = match.group("field")
        context = "\n".join(lines[max(0, index - 8) : min(len(lines), index + 3)])
        scope = nearest_function_name(lines, index)
        guard_status, line_kind, reason = classify_guard_status(
            line=line,
            context=context,
            scope=scope,
            writer_source=writer_source,
        )
        items.append(
            {
                "path": rel,
                "line": index + 1,
                "field": field,
                "guard_status": guard_status,
                "line_kind": line_kind,
                "reason": reason,
                "writer_source": writer_source,
                "write_allowed": False,
            }
        )
    return items


def classify_guard_status(*, line: str, context: str, scope: str, writer_source: bool) -> tuple[str, str, str]:
    if line.lstrip().startswith(("def ", "async def ")):
        return "reference_only", "schema_or_reference", "timestamp field appears in a function signature"
    if TIMESTAMP_CONDITION_RE.match(line):
        return "reference_only", "schema_or_reference", "timestamp field appears in a conditional read"
    if TIMESTAMP_AGE_CALCULATION_RE.search(line):
        return "reference_only", "schema_or_reference", "timestamp field is an age calculation anchor"
    if any(token in line for token in REFERENCE_ONLY_LINE_TOKENS):
        return "reference_only", "schema_or_reference", "timestamp field appears in a parser or read-only extraction line"
    if "args." in line and " or None" in line:
        return "reference_only", "schema_or_reference", "timestamp field is passed through from CLI args to a downstream parser"
    if RISKY_FALLBACK_RE.search(line):
        return "risky_literal_fallback", "risky_literal_fallback", "timestamp field can fall back to a non-parseable literal"
    if any(token in context for token in GUARD_TOKENS):
        return "guarded", "guarded_timestamp_source", "nearby code uses a known timestamp guard or ISO producer"
    line_kind = classify_line_kind(line=line, context=context, scope=scope)
    if any(token in line for token in MONOTONIC_RUNTIME_TOKENS) and line_kind == "unknown_writer_candidate":
        return "reference_only", "schema_or_reference", "timestamp field is a monotonic runtime age marker"
    if not writer_source:
        return "reference_only", line_kind, "timestamp field appears in a non-writer source"
    if line_kind == "schema_or_reference":
        return "reference_only", line_kind, "timestamp field appears in schema or reference code"
    if line_kind == "report_metadata":
        return "report_metadata_candidate", line_kind, "timestamp field appears in report or metrics metadata"
    if line_kind == "template_timestamp_constant":
        return "template_timestamp_candidate", line_kind, "timestamp field appears in a rendered text template"
    if line_kind == "direct_emitted_timestamp":
        return "direct_writer_candidate", line_kind, "timestamp field appears in a direct emitted write shape"
    return "unguarded_candidate", line_kind, "writer-like source references a timestamp field without a known guard nearby"


def classify_line_kind(*, line: str, context: str, scope: str = "") -> str:
    stripped = line.strip()
    lowered_line = stripped.lower()
    lowered_context = context.lower()
    if scope in REFERENCE_ONLY_SCOPE_NAMES:
        return "schema_or_reference"
    if any(token.lower() in lowered_line for token in SCHEMA_REFERENCE_TOKENS):
        return "schema_or_reference"
    if any(token in lowered_line or token in lowered_context for token in REPORT_METADATA_TOKENS):
        return "report_metadata"
    if TEMPLATE_FIELD_RE.match(stripped) and not stripped.startswith(("'", '"', "f'", 'f"')):
        return "template_timestamp_constant"
    if DIRECT_STRING_FIELD_RE.search(line) or re.search(r"['\"]\w+['\"]\s*:", line):
        return "direct_emitted_timestamp"
    return "unknown_writer_candidate"


def nearest_function_name(lines: list[str], index: int) -> str:
    for cursor in range(index, -1, -1):
        match = DEF_RE.match(lines[cursor])
        if match:
            return match.group("name")
    return ""


def is_potential_writer_source(lines: list[str]) -> bool:
    lowered = "\n".join(lines).lower()
    return any(token.lower() in lowered for token in WRITER_TOKENS)


def iter_source_files(app_root: Path) -> Iterable[Path]:
    pending = [Path(app_root)]
    while pending:
        current = pending.pop()
        try:
            children = sorted(current.iterdir(), key=lambda item: item.as_posix().lower())
        except OSError:
            continue
        for child in children:
            if is_skipped_source_path(app_root, child):
                continue
            if child.is_dir():
                child_name = child.name.lower()
                if child_name in SKIP_DIR_NAMES or any(child_name.startswith(prefix) for prefix in SKIP_DIR_PREFIXES):
                    continue
                pending.append(child)
                continue
            if not child.is_file() or child.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            if child.name.endswith("_manifest.py"):
                continue
            try:
                if child.stat().st_size > MAX_SOURCE_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield child


def is_skipped_source_path(app_root: Path, path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(Path(app_root).resolve()).as_posix().lower()
    except (OSError, ValueError):
        rel = path.as_posix().lower()
    rel = rel.strip("/")
    return any(rel == prefix or rel.startswith(prefix + "/") for prefix in SKIP_REL_PATH_PREFIXES)


def rel_to_root(app_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(Path(app_root).resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# XinYu Timestamp Writer Guard Audit",
        "",
        result["privacy_note"],
        "",
        f"- status: {result['status']}",
        f"- source_file_count: {result['source_file_count']}",
        f"- timestamp_writer_candidate_count: {result['timestamp_writer_candidate_count']}",
        "",
        "## Guard Status Counts",
        "",
    ]
    append_counts(lines, result.get("guard_status_counts") or {})
    lines.extend(["", "## Field Counts", ""])
    append_counts(lines, result.get("field_counts") or {})
    lines.extend(["", "## Line Kind Counts", ""])
    append_counts(lines, result.get("line_kind_counts") or {})
    lines.extend(["", "## Items", ""])
    items = result.get("items") or []
    if not items:
        lines.append("- none")
    else:
        for item in items:
            lines.append(
                f"- `{item['path']}`:{item['line']} | field={item['field']} | "
                f"guard={item['guard_status']} | line_kind={item['line_kind']} | "
                f"writer_source={str(item['writer_source']).lower()} | "
                f"reason={item['reason']} | write_allowed=false"
            )
    return "\n".join(lines).rstrip() + "\n"


def append_counts(lines: list[str], counts: dict[str, int]) -> None:
    if not counts:
        lines.append("- none")
        return
    for name, count in counts.items():
        lines.append(f"- {name}: {count}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit timestamp writer guard coverage without reading memory bodies.")
    parser.add_argument("--app-root", type=Path, default=APP_ROOT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = build_timestamp_writer_guard_audit(args.app_root)
    output = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if args.json else render_markdown(result)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
