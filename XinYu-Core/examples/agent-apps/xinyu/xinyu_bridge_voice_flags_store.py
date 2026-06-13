from __future__ import annotations

import os
from pathlib import Path

from state_service import atomic_write_text


def read_voice_flag_env(name: str) -> str:
    return os.environ.get(name, "")


def write_voice_flag_env(name: str, value: str) -> None:
    os.environ[name] = value


def read_voice_flags_env_file_lines(path: Path) -> list[str]:
    path = Path(path)
    try:
        if not path.exists():
            return []
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def write_voice_flags_env_file_lines(path: Path, lines: list[str]) -> None:
    atomic_write_text(Path(path), "\n".join(lines))
