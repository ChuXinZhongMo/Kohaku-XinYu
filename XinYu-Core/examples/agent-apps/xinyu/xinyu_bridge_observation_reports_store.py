from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text
from state_service import read_text_safe


def observation_report_exists(path: Path) -> bool:
    return Path(path).exists()


def read_observation_report_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8-sig", errors="replace")


def read_observation_report_text_safe(path: Path, default: str = "") -> str:
    return read_text_safe(Path(path), default=default)


def write_observation_report_text(path: Path, text: str) -> None:
    atomic_write_text(Path(path), text)
