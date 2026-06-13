from __future__ import annotations

import os
from pathlib import Path


def bootstrap_env_file_exists(path: Path) -> bool:
    return Path(path).exists()


def read_bootstrap_env_file_lines(path: Path) -> list[str]:
    return Path(path).read_text(encoding="utf-8").splitlines()


def bootstrap_env_has_key(name: str) -> bool:
    return name in os.environ


def write_bootstrap_env(name: str, value: str) -> None:
    os.environ[name] = value
