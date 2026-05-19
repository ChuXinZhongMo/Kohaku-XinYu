from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from git_change_group_audit import ChangeEntry, classify_change, collect_git_status, parse_short_status


APP_REL = Path("XinYu-Core/examples/agent-apps/xinyu")
REFERENCE_GLOBS = (
    "!memory/**",
    "!runtime/**",
    "!data/**",
    "!library/**",
    "!cases/**",
    "!__pycache__/**",
    "!.pytest_cache/**",
)


@dataclass(frozen=True)
class ArchiveDeleteCandidate:
    path: str
    name: str
    candidate_kind: str
    relocation_examples: tuple[str, ...]
    reference_examples: tuple[str, ...]

    @property
    def reference_count(self) -> int:
        return len(self.reference_examples)

    @property
    def relocation_count(self) -> int:
        return len(self.relocation_examples)

    @property
    def decision(self) -> str:
        if self.relocation_count:
            return "accept_delete_relocated"
        if self.reference_count:
            return "hold_delete_referenced"
        return "accept_delete_no_live_refs"


def build_archive_delete_reference_audit(
    repo_root: Path,
    *,
    entries: list[ChangeEntry] | None = None,
    max_examples: int = 8,
) -> dict[str, Any]:
    root = repo_root.resolve()
    status_entries = entries if entries is not None else collect_git_status(root)
    app_root = root / APP_REL
    file_index = _build_file_index(app_root)
    reference_index = _build_reference_index(app_root)
    candidates = [
        _candidate_for_entry(
            root,
            entry,
            file_index=file_index,
            reference_index=reference_index,
            max_examples=max_examples,
        )
        for entry in status_entries
        if "D" in entry.status and _is_archive_delete_entry(entry, file_index)
    ]
    candidates.sort(key=lambda item: (item.decision, item.candidate_kind, item.path))
    by_decision = Counter(item.decision for item in candidates)
    by_kind = Counter(item.candidate_kind for item in candidates)
    return {
        "total_candidates": len(candidates),
        "by_decision": dict(sorted(by_decision.items())),
        "by_kind": dict(sorted(by_kind.items())),
        "items": [
            {
                "path": item.path,
                "name": item.name,
                "candidate_kind": item.candidate_kind,
                "decision": item.decision,
                "relocation_count": item.relocation_count,
                "relocation_examples": list(item.relocation_examples),
                "reference_count": item.reference_count,
                "reference_examples": list(item.reference_examples),
            }
            for item in candidates
        ],
        "privacy_note": "Generated from git status paths plus source-code/doc reference file names only; does not read or print private memory, runtime, QQ payloads, tokens, or data bodies.",
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# XinYu Archive/Delete Reference Audit",
        "",
        "Generated from `git status --short` deleted cleanup candidates plus path/reference checks.",
        "It does not read or print private memory, runtime, QQ payloads, tokens, or data bodies.",
        "",
        f"- total_candidates: {audit['total_candidates']}",
        "",
        "## Decision Counts",
        "",
    ]
    for decision, count in (audit.get("by_decision") or {}).items():
        lines.append(f"- {decision}: {count}")
    lines.extend(["", "## Kind Counts", ""])
    for kind, count in (audit.get("by_kind") or {}).items():
        lines.append(f"- {kind}: {count}")
    lines.extend(["", "## Items", ""])
    for item in audit.get("items") or []:
        lines.append(
            f"- `{item['path']}` | kind={item['candidate_kind']} | decision={item['decision']} | "
            f"relocated={item['relocation_count']} | refs={item['reference_count']}"
        )
        if item.get("relocation_examples"):
            lines.append("  - relocation_examples:")
            for example in item["relocation_examples"]:
                lines.append(f"    - `{example}`")
        if item.get("reference_examples"):
            lines.append("  - reference_examples:")
            for example in item["reference_examples"]:
                lines.append(f"    - `{example}`")
    lines.extend(
        [
            "",
            "## Safety Rule",
            "",
            "- `accept_delete_relocated` means a same-name replacement exists under the active tree.",
            "- `accept_delete_no_live_refs` means the deleted path/name had no live source/doc references in this audit.",
            "- `hold_delete_referenced` means do not accept deletion until the listed references are reviewed.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _candidate_for_entry(
    repo_root: Path,
    entry: ChangeEntry,
    *,
    file_index: dict[str, list[str]],
    reference_index: list[tuple[str, str]],
    max_examples: int,
) -> ArchiveDeleteCandidate:
    path = entry.path
    name = Path(path).name
    relocations = _find_relocations(file_index, path, name, max_examples=max_examples)
    refs = _find_reference_files(reference_index, path, name, max_examples=max_examples)
    return ArchiveDeleteCandidate(
        path=path,
        name=name,
        candidate_kind=_candidate_kind(path),
        relocation_examples=tuple(relocations),
        reference_examples=tuple(refs),
    )


def _is_archive_delete_entry(entry: ChangeEntry, file_index: dict[str, list[str]]) -> bool:
    if classify_change(entry.path, entry.status) == "archive/delete":
        return True
    name = Path(entry.path).name
    return bool(_find_relocations(file_index, entry.path, name, max_examples=1))


def _find_relocations(file_index: dict[str, list[str]], deleted_path: str, name: str, *, max_examples: int) -> list[str]:
    deleted_rel = _app_rel(deleted_path)
    matches: list[str] = []
    for rel in file_index.get(name, []):
        if rel == deleted_rel:
            continue
        if rel.startswith(
            ("tests/smoke/", "ops/manual/", "ops/probes/", "ops/diagnostics/", "ops/validation/", "ops/archive/", "tools/")
        ):
            matches.append((APP_REL / rel).as_posix())
    return sorted(matches)[:max_examples]


def _build_file_index(app_root: Path) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for rel, _path in _iter_scannable_files(app_root):
        index.setdefault(Path(rel).name, []).append(rel)
    for refs in index.values():
        refs.sort()
    return index


def _build_reference_index(app_root: Path) -> list[tuple[str, str]]:
    if not app_root.exists():
        return []
    allowed_suffixes = {".py", ".md", ".yaml", ".yml", ".ps1", ".ts", ".tsx", ".js", ".json"}
    index: list[tuple[str, str]] = []
    for rel, path in _iter_scannable_files(app_root):
        if path.suffix.lower() not in allowed_suffixes:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        index.append(((APP_REL / rel).as_posix(), text))
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
            parts = Path(rel).parts
            if path.is_dir():
                if _skip_reference_rel(parts):
                    continue
                pending.append(path)
                continue
            if _skip_reference_rel(parts):
                continue
            files.append((rel, path))
    return files


def _skip_reference_rel(parts: tuple[str, ...]) -> bool:
    if not parts:
        return False
    if parts[0] in {"memory", "runtime", "data", "library", "cases", "logs"}:
        return True
    if len(parts) >= 2 and parts[:2] == ("ops", "reports"):
        return True
    if any(part in {".git", ".pytest_cache", "__pycache__", ".venv", "node_modules", "dist", "build"} for part in parts):
        return True
    return any(part.startswith("codex-qq-") for part in parts)


def _find_reference_files(reference_index: list[tuple[str, str]], deleted_path: str, name: str, *, max_examples: int) -> list[str]:
    deleted_rel = _app_rel(deleted_path)
    needles = _reference_needles(deleted_rel, name)
    examples: list[str] = []
    deleted_repo_rel = (APP_REL / deleted_rel).as_posix()
    for rel_to_repo, text in reference_index:
        if rel_to_repo == deleted_repo_rel:
            continue
        if rel_to_repo.endswith(
            (
                "ops/validation/archive_delete_reference_audit.py",
                "tests/test_archive_delete_reference_audit.py",
            )
        ):
            continue
        if any(needle in text for needle in needles):
            examples.append(rel_to_repo)
            if len(examples) >= max_examples:
                return examples
    return examples


def _reference_needles(deleted_rel: str, name: str) -> tuple[str, ...]:
    stem = Path(name).stem
    needles = [deleted_rel, name]
    if stem and stem not in needles:
        needles.append(stem)
    return tuple(needles)


def _candidate_kind(path: str) -> str:
    rel = _app_rel(path)
    name = Path(rel).name
    if rel.startswith("xinyu_v1/"):
        return "core_orphan"
    if name.endswith(".md") or rel.startswith(("context/", "tools/")):
        return "ops_orphan"
    if name.endswith("_smoke.py"):
        return "root_smoke"
    if name.startswith("manual_"):
        return "root_manual_runner"
    if name.startswith(("diagnose_", "check_")):
        return "root_diagnostic"
    if name.startswith("validate_") or name == "sync_memory_seeds.py":
        return "root_validator"
    if name in {"xinyu_live_module_diagnostics.py", "xinyu_research_loop_dry_run.py"}:
        return "root_probe"
    if rel.startswith("custom/") and name.endswith("_manifest.py"):
        return "custom_manifest"
    return "cleanup_candidate"


def _app_rel(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    prefix = APP_REL.as_posix() + "/"
    if normalized.startswith(prefix):
        return normalized[len(prefix) :]
    return normalized


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit deleted archive/cleanup candidates for live references.")
    parser.add_argument("--repo-root", default="D:\\XinYu")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default="")
    parser.add_argument("--max-examples", type=int, default=8)
    parser.add_argument("--from-status-file", default="")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    entries = None
    if args.from_status_file:
        entries = parse_short_status(Path(args.from_status_file).read_text(encoding="utf-8"))
    audit = build_archive_delete_reference_audit(
        Path(args.repo_root),
        entries=entries,
        max_examples=args.max_examples,
    )
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
