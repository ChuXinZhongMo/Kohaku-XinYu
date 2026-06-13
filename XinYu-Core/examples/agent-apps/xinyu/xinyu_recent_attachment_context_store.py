from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import atomic_write_json
from state_service import read_json
from state_service import read_text_safe


def read_recent_attachment_context_json(path: Path) -> Any:
    return read_json(path, default={"attachments": []})


def write_recent_attachment_context_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_json(path, data, sort_keys=True)


def read_recent_attachment_text(path: Path) -> str:
    return read_text_safe(path)
