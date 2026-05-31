from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


APP_REL = Path("XinYu-Core/examples/agent-apps/xinyu")
TEXT_SUFFIXES = {".md", ".json", ".jsonl", ".yaml", ".yml", ".txt"}
SKIP_DIR_NAMES = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "codex_pytest_tmp",
    "codex_tmp",
    "pytest-tmp",
    "pytest_tmp",
}
MAX_METADATA_FILE_BYTES = 2_000_000


@dataclass(frozen=True)
class BoundaryRecord:
    path: str
    zone: str
    declared_type: str = ""
    source: str = ""
    concern: str = ""


def app_root(repo_root: Path) -> Path:
    return repo_root / APP_REL


def collect_boundary_records(repo_root: Path) -> list[BoundaryRecord]:
    app = app_root(repo_root)
    candidates = (
        app / "memory",
        repo_root / "assets" / "cases",
        repo_root / "assets" / "library",
        repo_root / "cases",
        repo_root / "library",
        app / "data",
        app / "runtime",
    )
    records: list[BoundaryRecord] = []
    for root in candidates:
        if not root.exists():
            continue
        for path in _iter_small_metadata_files(root):
            rel = _rel(repo_root, path)
            zone = classify_zone(repo_root, path)
            fields = frontmatter_fields(path)
            concern = boundary_concern(rel, zone, fields)
            records.append(
                BoundaryRecord(
                    path=rel,
                    zone=zone,
                    declared_type=fields.get("memory_type", ""),
                    source=fields.get("source", ""),
                    concern=concern,
                )
            )
    return records


def classify_zone(repo_root: Path, path: Path) -> str:
    rel = _rel(repo_root, path)
    app_prefix = APP_REL.as_posix() + "/"
    app_rel = rel[len(app_prefix) :] if rel.startswith(app_prefix) else rel
    if rel.startswith("assets/cases/") or rel.startswith("cases/"):
        return "cases"
    if rel.startswith("assets/library/") or rel.startswith("library/"):
        return "library"
    if app_rel.startswith("memory/"):
        if app_rel.startswith("memory/knowledge/"):
            return "memory.knowledge"
        if app_rel.startswith("memory/context/") or app_rel.startswith("memory/self/"):
            return "memory.runtime_or_self"
        return "memory"
    if app_rel.startswith("data/conversation_experience/"):
        return "legacy.cases"
    if app_rel.startswith("data/external/"):
        return "legacy.library"
    if app_rel.startswith("data/"):
        return "legacy.data"
    if app_rel.startswith("runtime/"):
        return "runtime"
    return "unknown"


def frontmatter_fields(path: Path) -> dict[str, str]:
    if path.suffix.lower() != ".md":
        return {}
    fields: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[:80]
    except OSError:
        return fields
    if not lines or lines[0].strip() != "---":
        return fields
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        if key in {"memory_type", "source", "status", "time_scope"}:
            fields[key] = value.strip()
    return fields


def boundary_concern(rel: str, zone: str, fields: dict[str, str]) -> str:
    memory_type = fields.get("memory_type", "")
    source = fields.get("source", "").lower()
    lower_path = rel.lower()
    if zone.startswith("legacy."):
        return "legacy_fallback_review"
    if zone == "library" and memory_type:
        return "library_file_has_memory_frontmatter"
    if zone == "cases" and memory_type and "case" not in memory_type:
        return "case_file_declares_non_case_memory_type"
    if zone.startswith("memory") and lower_path.endswith((".jsonl", ".json")) and "/events/" not in lower_path:
        return "structured_data_inside_memory_review"
    if zone.startswith("memory") and any(marker in source for marker in ("dataset", "kaggle", "huggingface")):
        return "external_dataset_source_inside_memory"
    if zone == "runtime" and memory_type:
        return "runtime_file_has_stable_memory_frontmatter"
    return ""


def summarize(records: list[BoundaryRecord]) -> dict[str, object]:
    zone_counts = Counter(record.zone for record in records)
    concern_counts = Counter(record.concern for record in records if record.concern)
    concerns = [
        {
            "path": record.path,
            "zone": record.zone,
            "declared_type": record.declared_type,
            "source": record.source,
            "concern": record.concern,
        }
        for record in records
        if record.concern
    ]
    return {
        "total_files": len(records),
        "zone_counts": dict(sorted(zone_counts.items())),
        "concern_counts": dict(sorted(concern_counts.items())),
        "concerns": concerns[:120],
    }


def render_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# XinYu Memory/Library/Cases Boundary Audit",
        "",
        "This report scans paths and small frontmatter metadata only.",
        "It does not print memory bodies, QQ logs, or private content.",
        "",
        f"- total_files: {summary['total_files']}",
        "",
        "## Zone Counts",
        "",
    ]
    for zone, count in (summary.get("zone_counts") or {}).items():
        lines.append(f"- {zone}: {count}")
    lines.extend(["", "## Concern Counts", ""])
    concern_counts = summary.get("concern_counts") or {}
    if concern_counts:
        for concern, count in concern_counts.items():
            lines.append(f"- {concern}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Review Items", ""])
    concerns = summary.get("concerns") or []
    if not concerns:
        lines.append("- none")
    else:
        for item in concerns:
            lines.append(
                f"- `{item['path']}` | zone={item['zone']} | "
                f"type={item['declared_type'] or 'none'} | concern={item['concern']}"
            )
    return "\n".join(lines).rstrip() + "\n"


def _iter_small_metadata_files(root: Path):
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


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit XinYu memory/library/cases path boundaries without printing bodies.")
    parser.add_argument("--repo-root", default="D:\\XinYu")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default="")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    summary = summarize(collect_boundary_records(Path(args.repo_root)))
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        if args.json:
            output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            output.write_text(render_markdown(summary), encoding="utf-8")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
