from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


APP_REL = Path("XinYu-Core/examples/agent-apps/xinyu")
DEFAULT_SMOKE_DIRS = (
    Path("tests/smoke/learning/integration"),
    Path("tests/smoke/memory/integration"),
)


def build_restore_guard_report(app_root: Path, smoke_dirs: tuple[Path, ...] = DEFAULT_SMOKE_DIRS) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for smoke_dir in smoke_dirs:
        directory = app_root / smoke_dir
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*_smoke.py")):
            entries.append(inspect_smoke(path, app_root=app_root))

    mutation_capable = [entry for entry in entries if entry["mutation_capable"]]
    missing_restore = [entry for entry in mutation_capable if not entry["supports_restore_after"]]
    missing_diff_suppression = [entry for entry in mutation_capable if not entry["supports_diff_lines"]]
    return {
        "total_smokes": len(entries),
        "mutation_capable_count": len(mutation_capable),
        "restore_after_supported_count": sum(1 for entry in mutation_capable if entry["supports_restore_after"]),
        "diff_suppression_supported_count": sum(1 for entry in mutation_capable if entry["supports_diff_lines"]),
        "missing_restore_count": len(missing_restore),
        "missing_diff_suppression_count": len(missing_diff_suppression),
        "entries": entries,
        "privacy_note": "Generated from smoke source files only; does not read memory bodies, QQ payloads, tokens, or secrets.",
    }


def inspect_smoke(path: Path, *, app_root: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    mutation_capable = any(
        marker in text
        for marker in (
            "MUTATION SUMMARY",
            "_restore_snapshot",
            "_snapshot(",
            "TRACKED_FILES",
            "_prepare_case(",
        )
    )
    supports_restore_after = "--restore-after" in text and "_restore_snapshot" in text
    supports_diff_lines = "--diff-lines" in text
    restore_default_on = "default=True" in text and "--restore-after" in text
    rel = path.resolve().relative_to(app_root.resolve()).as_posix()
    recommended_args = ["--restore-after"] if mutation_capable and supports_restore_after else []
    if mutation_capable and supports_diff_lines:
        recommended_args.extend(["--diff-lines", "0"])
    return {
        "path": rel,
        "mutation_capable": mutation_capable,
        "supports_restore_after": supports_restore_after,
        "supports_diff_lines": supports_diff_lines,
        "restore_default_on": restore_default_on,
        "recommended_args": recommended_args,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# XinYu Mutation Smoke Restore Guard",
        "",
        "Generated from smoke source files only.",
        "It does not read or print memory bodies, QQ payloads, tokens, or secrets.",
        "",
        f"- total_smokes: {report['total_smokes']}",
        f"- mutation_capable_count: {report['mutation_capable_count']}",
        f"- restore_after_supported_count: {report['restore_after_supported_count']}",
        f"- diff_suppression_supported_count: {report['diff_suppression_supported_count']}",
        f"- missing_restore_count: {report['missing_restore_count']}",
        f"- missing_diff_suppression_count: {report['missing_diff_suppression_count']}",
        "",
        "## Mutation-Capable Smokes",
        "",
    ]
    for entry in report.get("entries") or []:
        if not entry.get("mutation_capable"):
            continue
        recommended = " ".join(entry.get("recommended_args") or []) or "none"
        lines.append(
            f"- `{entry['path']}` | restore_after={_yes_no(entry['supports_restore_after'])} | "
            f"diff_lines={_yes_no(entry['supports_diff_lines'])} | default_restore={_yes_no(entry['restore_default_on'])} | "
            f"recommended=`{recommended}`"
        )
    lines.extend(
        [
            "",
            "## Rule",
            "",
            "- Mutation-capable smoke scripts should be run with `--restore-after`.",
            "- When a smoke supports diff rendering, use `--diff-lines 0` during autonomous validation.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _yes_no(value: Any) -> str:
    return "yes" if value else "no"


def _parse_smoke_dirs(raw: list[str]) -> tuple[Path, ...]:
    if not raw:
        return DEFAULT_SMOKE_DIRS
    return tuple(Path(item) for item in raw)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit mutation-capable smokes for restore-after safety.")
    parser.add_argument("--repo-root", default="D:\\XinYu")
    parser.add_argument("--app-root", default="")
    parser.add_argument("--smoke-dir", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default="")
    parser.add_argument("--strict", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    repo_root = Path(args.repo_root)
    app_root = Path(args.app_root) if args.app_root else repo_root / APP_REL
    report = build_restore_guard_report(app_root, smoke_dirs=_parse_smoke_dirs(args.smoke_dir))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.json else render_markdown(report)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if args.strict and report["missing_restore_count"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
