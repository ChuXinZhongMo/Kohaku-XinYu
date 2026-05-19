from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


APP_PREFIX = "XinYu-Core/examples/agent-apps/xinyu/"


@dataclass(frozen=True)
class ChangeEntry:
    status: str
    path: str


def parse_short_status(text: str) -> list[ChangeEntry]:
    entries: list[ChangeEntry] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        if len(raw) < 4:
            continue
        status = raw[:2]
        path = raw[3:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[-1]
        entries.append(ChangeEntry(status=status, path=_norm(path)))
    return entries


def classify_change(path: str, status: str = "") -> str:
    rel = _norm(path)
    app_rel = rel[len(APP_PREFIX) :] if rel.startswith(APP_PREFIX) else rel
    name = Path(app_rel).name

    if rel.startswith(("Start-XinYu-Desktop.", "Stop-XinYu-Desktop.")):
        return "desktop"
    if rel.startswith(("Start-XinYu-TinyKernel.", "Stop-XinYu-TinyKernel.")):
        return "ops"
    if rel == "XinYu-TinyKernel" or rel.startswith("XinYu-TinyKernel/"):
        return "core"
    if rel.startswith("XinYu_Desktop/"):
        return "desktop"
    if rel.startswith("XinYu-Core/src/xinyu_runtime/"):
        return "core"
    if rel.startswith("diagnostics/"):
        return "ops"
    if rel.startswith("XinYu-Core/memory/"):
        return "memory-data"
    if rel in {".gitignore", "pytest.ini"} or app_rel in {"config.yaml", "pytest.ini", "xinyu.local.env.example"}:
        return "ops"
    if rel.startswith("worklog/"):
        return "ops"
    if _is_archived_or_deleted(app_rel, status):
        return "archive/delete"
    if app_rel.startswith(("memory/", "memory-seeds/", "cases/", "library/", "data/")):
        return "memory-data"
    if rel == "plan.md" or app_rel.endswith(".md") or app_rel.startswith("project-plans/"):
        return "docs"
    if app_rel.startswith("tests/") or name.endswith("_smoke.py"):
        return "tests"
    if app_rel.startswith(("ops/", "tools/")) or name in {
        "smoke_run.py",
        "long_run_status.py",
        "run_local_xinyu.py",
        "sync_memory_seeds.py",
        "validate_inner_framework.py",
        "validate_scaffold.py",
    }:
        return "ops"
    if app_rel.startswith("stores/") or name in {"state_service.py", "xinyu_storage_paths.py"}:
        return "stores"
    if app_rel.startswith("services/") or name in {
        "xinyu_chat_service.py",
        "xinyu_codex_service.py",
        "xinyu_learning_service.py",
        "xinyu_daily_digest.py",
    }:
        return "services"
    if app_rel.startswith("custom/"):
        return "core"
    if name.startswith(("xinyu_qq_", "xinyu_bridge_", "xinyu_desktop_")):
        return "adapters"
    if name.startswith("xinyu_") or name.startswith("v1_") or app_rel.startswith("xinyu_v1/"):
        return "core"
    return "unknown"


def summarize(entries: list[ChangeEntry]) -> dict[str, object]:
    by_group: dict[str, list[ChangeEntry]] = defaultdict(list)
    by_status = Counter()
    for entry in entries:
        group = classify_change(entry.path, entry.status)
        by_group[group].append(entry)
        by_status[_status_label(entry.status)] += 1
    return {
        "total": len(entries),
        "by_status": dict(sorted(by_status.items())),
        "by_group": {
            group: {
                "count": len(items),
                "examples": [item.path for item in items[:8]],
            }
            for group, items in sorted(by_group.items())
        },
    }


def render_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# XinYu Change Group Audit",
        "",
        "This report is generated from `git status --short` paths only.",
        "It does not read or print memory file contents.",
        "",
        f"- total_entries: {summary['total']}",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in (summary.get("by_status") or {}).items():
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Group Counts", ""])
    by_group = summary.get("by_group") or {}
    for group, payload in by_group.items():
        assert isinstance(payload, dict)
        lines.append(f"### {group}")
        lines.append(f"- count: {payload['count']}")
        examples = payload.get("examples") or []
        if examples:
            lines.append("- examples:")
            for example in examples:
                lines.append(f"  - `{example}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def collect_git_status(repo_root: Path) -> list[ChangeEntry]:
    completed = subprocess.run(
        ["git", "status", "--short"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip())
    return parse_short_status(completed.stdout)


def _status_label(status: str) -> str:
    clean = status.strip()
    if clean == "??":
        return "untracked"
    if "D" in status:
        return "deleted"
    if "A" in status:
        return "added"
    if "M" in status:
        return "modified"
    if "R" in status:
        return "renamed"
    return clean or "unknown"


def _is_archived_or_deleted(app_rel: str, status: str) -> bool:
    name = Path(app_rel).name
    if "D" not in status:
        return False
    if name.endswith("_smoke.py"):
        return True
    if name.startswith("manual_") or name.startswith("diagnose_") or name.startswith("check_"):
        return True
    if app_rel.startswith("custom/") and name.endswith("_manifest.py"):
        return True
    if name in {
        "dialogue_curiosity_review.py",
        "goldmark_dehydrate.py",
        "life_memory_visible_probe.py",
        "long_lived_session_harness.py",
        "mark_smoke_test.py",
        "memory_lived_pressure_arc.py",
        "sync_memory_seeds.py",
        "validate_inner_framework.py",
        "validate_scaffold.py",
        "xinyu_live_module_diagnostics.py",
        "xinyu_research_loop_dry_run.py",
    }:
        return True
    return False


def _norm(path: str) -> str:
    return path.replace("\\", "/").strip().strip('"')


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Group git status paths by XinYu capability area.")
    parser.add_argument("--repo-root", default="D:\\XinYu")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default="")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    repo_root = Path(args.repo_root)
    summary = summarize(collect_git_status(repo_root))
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
