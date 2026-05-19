from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
from pathlib import Path


DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "logs",
    "memory",
    "runtime",
}

ANY_DEPTH_EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
}

DEFAULT_EXCLUDED_GLOBS = {
    "codex-qq-*",
    "context/**",
    "data/external/**",
    "data/replay/private/**",
    "data/replay/sanitized/**",
    "emotions/**",
    "learning/owner_supplied/**",
    "learning/self_found/**",
    "self/**",
    "test-temp-*",
    "xinyu-qq-gateway-image-*",
    "xinyu-qq-outbox-*",
}

EXPERIMENT_MARKERS = (
    "smoke",
    "trial",
    "shadow",
    "canary",
    "baseline",
    "harness",
)


@dataclass(frozen=True)
class FileStat:
    path: str
    lines: int
    bytes: int


def scan(
    root: Path,
    *,
    excluded_dirs: set[str] | None = None,
    excluded_globs: set[str] | None = None,
    largest_limit: int = 25,
) -> dict[str, object]:
    root = root.resolve()
    excluded = set(DEFAULT_EXCLUDED_DIRS if excluded_dirs is None else excluded_dirs)
    excluded_patterns = set(DEFAULT_EXCLUDED_GLOBS if excluded_globs is None else excluded_globs)
    py_files: list[Path] = []
    md_files = 0
    total_files = 0
    root_py_files = 0
    smoke_like_files = 0
    migrated_smoke_files = 0
    package_dirs: dict[str, int] = {}

    for path in root.rglob("*"):
        rel_parts = path.relative_to(root).parts
        rel = path.relative_to(root).as_posix()
        if _is_excluded(path, rel_parts=rel_parts, rel=rel, excluded_dirs=excluded, excluded_globs=excluded_patterns):
            continue
        if not path.is_file():
            continue
        total_files += 1
        if path.suffix == ".md":
            md_files += 1
        if path.suffix != ".py":
            continue
        py_files.append(path)
        rel_path = path.relative_to(root).as_posix()
        lower_rel = rel_path.lower()
        lower_name = path.name.lower()
        if lower_rel.startswith("tests/smoke/") and (
            lower_name.startswith(("manual_", "diagnose_")) or any(marker in lower_name for marker in EXPERIMENT_MARKERS)
        ):
            migrated_smoke_files += 1
        if path.parent == root:
            root_py_files += 1
            if lower_name.startswith(("manual_", "diagnose_")) or any(marker in lower_name for marker in EXPERIMENT_MARKERS):
                smoke_like_files += 1
        first_dir = path.relative_to(root).parts[0] if len(path.relative_to(root).parts) > 1 else "."
        package_dirs[first_dir] = package_dirs.get(first_dir, 0) + 1

    largest = sorted((_file_stat(root, path) for path in py_files), key=lambda item: item.lines, reverse=True)[
        : max(1, largest_limit)
    ]
    total_lines = sum(item.lines for item in largest) + sum(
        _line_count(path) for path in py_files if path.relative_to(root).as_posix() not in {item.path for item in largest}
    )

    return {
        "root": str(root),
        "excluded_dirs": sorted(excluded),
        "excluded_globs": sorted(excluded_patterns),
        "totals": {
            "files": total_files,
            "python_files": len(py_files),
            "markdown_files": md_files,
            "python_lines": total_lines,
            "root_python_files": root_py_files,
            "root_experiment_like_python_files": smoke_like_files,
            "tests_smoke_python_files": migrated_smoke_files,
        },
        "package_dirs": dict(sorted(package_dirs.items(), key=lambda item: (-item[1], item[0]))),
        "largest_python_files": [asdict(item) for item in largest],
        "signals": _signals(root_py_files=root_py_files, smoke_like_files=smoke_like_files, largest=largest),
    }


def _signals(*, root_py_files: int, smoke_like_files: int, largest: list[FileStat]) -> list[str]:
    signals: list[str] = []
    if root_py_files > 120:
        signals.append("root_python_surface_large")
    if smoke_like_files > 40:
        signals.append("root_experiment_files_should_move_to_tests_or_tools")
    if largest and largest[0].lines > 2500:
        signals.append("largest_module_should_keep_shrinking")
    if sum(1 for item in largest if item.lines > 1000) >= 6:
        signals.append("many_oversized_modules")
    return signals


def _is_excluded(
    path: Path,
    *,
    rel_parts: tuple[str, ...],
    rel: str,
    excluded_dirs: set[str],
    excluded_globs: set[str],
) -> bool:
    if path.is_file() and any(part in excluded_dirs for part in rel_parts[:-1]):
        first = rel_parts[0] if rel_parts else ""
        return first in excluded_dirs or any(part in ANY_DEPTH_EXCLUDED_DIRS for part in rel_parts[:-1])
    if path.is_dir() and any(part in excluded_dirs for part in rel_parts):
        first = rel_parts[0] if rel_parts else ""
        if first not in excluded_dirs and not any(part in ANY_DEPTH_EXCLUDED_DIRS for part in rel_parts):
            return False
        return True
    return any(fnmatch(rel, pattern) or fnmatch(rel + "/", pattern) for pattern in excluded_globs)


def _file_stat(root: Path, path: Path) -> FileStat:
    return FileStat(path=path.relative_to(root).as_posix(), lines=_line_count(path), bytes=path.stat().st_size)


def _line_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize XinYu source structure without runtime/private state noise.")
    parser.add_argument("root", nargs="?", default=".", help="Project root to scan.")
    parser.add_argument("--include-runtime", action="store_true", help="Include runtime, memory, logs, and local env dirs.")
    parser.add_argument("--include-generated", action="store_true", help="Include gitignored generated learning/codex data.")
    parser.add_argument("--largest", type=int, default=25, help="Number of largest Python files to report.")
    args = parser.parse_args(argv)

    excluded = set() if args.include_runtime else set(DEFAULT_EXCLUDED_DIRS)
    excluded_globs = set() if args.include_generated else set(DEFAULT_EXCLUDED_GLOBS)
    report = scan(Path(args.root), excluded_dirs=excluded, excluded_globs=excluded_globs, largest_limit=args.largest)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
