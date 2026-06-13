from __future__ import annotations

import subprocess
from pathlib import Path


SKIP_SCAN_DIRS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "memory",
    "runtime",
    "data",
    "library",
    "cases",
    "logs",
}
SKIP_SCAN_PREFIXES = {
    ("ops", "reports"),
}
MODULE_ECOLOGY_SCAN_SUFFIXES = {".py", ".ps1", ".md", ".yaml", ".yml", ".json"}
MODULE_ECOLOGY_REFERENCE_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".ps1", ".ts", ".tsx", ".js", ".json"}


def collect_module_ecology_paths(app_root: Path, *, max_items: int) -> list[str]:
    if not app_root.exists():
        return []
    paths: list[str] = []
    pending = [app_root]
    while pending and len(paths) < max_items:
        current = pending.pop()
        try:
            children = sorted(current.iterdir(), key=lambda item: item.as_posix().lower())
        except OSError:
            continue
        for child in children:
            rel = child.relative_to(app_root).as_posix()
            parts = Path(rel).parts
            if child.is_dir():
                if _skip_scan_parts(parts):
                    continue
                pending.append(child)
                continue
            if _skip_scan_parts(parts):
                continue
            if child.suffix.lower() in MODULE_ECOLOGY_SCAN_SUFFIXES:
                paths.append(rel)
                if len(paths) >= max_items:
                    break
    return sorted(paths)


def read_module_ecology_reference_sources(app_root: Path, *, max_items: int = 5000) -> list[tuple[str, str]]:
    sources: list[tuple[str, str]] = []
    for rel in collect_module_ecology_paths(app_root, max_items=max_items):
        path = app_root / rel
        if path.suffix.lower() not in MODULE_ECOLOGY_REFERENCE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        sources.append((rel, text))
    return sources


def read_module_ecology_git_status_text(app_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(app_root), "-c", "core.quotepath=false", "status", "--short", "--", "."],
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout


def read_module_ecology_status_file(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def write_module_ecology_output(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _skip_scan_parts(parts: tuple[str, ...]) -> bool:
    if not parts:
        return False
    if parts[0] in SKIP_SCAN_DIRS:
        return True
    return any(len(parts) >= len(prefix) and parts[: len(prefix)] == prefix for prefix in SKIP_SCAN_PREFIXES)
