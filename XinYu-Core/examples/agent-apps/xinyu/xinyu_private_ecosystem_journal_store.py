from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import read_text_safe


def append_private_ecosystem_journal_event(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)


def read_private_ecosystem_journal_text(path: Path) -> str:
    return read_text_safe(path)
