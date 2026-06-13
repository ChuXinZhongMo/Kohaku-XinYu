from __future__ import annotations

from pathlib import Path


def codex_report_is_file(path: Path) -> bool:
    return path.is_file()


def codex_report_mtime(path: Path) -> float:
    return path.stat().st_mtime


def read_codex_report_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def read_codex_report_text_for_update(path: Path) -> tuple[bool, str]:
    try:
        return True, read_codex_report_text(path).rstrip()
    except OSError:
        return False, ""


def write_codex_report_text(path: Path, text: str) -> bool:
    try:
        path.write_text(text, encoding="utf-8")
    except OSError:
        return False
    return True
