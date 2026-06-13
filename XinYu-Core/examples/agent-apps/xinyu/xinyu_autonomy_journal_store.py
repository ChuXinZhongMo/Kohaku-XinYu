from __future__ import annotations

import os
from pathlib import Path


def read_autonomy_journal_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def read_autonomy_journal_env_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8-sig", errors="replace").splitlines()


def autonomy_journal_env_has_key(name: str) -> bool:
    return name in os.environ


def write_autonomy_journal_env(name: str, value: str) -> None:
    os.environ[name] = value


def write_autonomy_journal_thought(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig")
