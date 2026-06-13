from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_json
from state_service import atomic_write_text
from state_service import read_json
from state_service import read_text_safe


def read_action_experience_digest_text(path: Path) -> str:
    return read_text_safe(path)


def write_action_experience_digest_text(path: Path, text: str) -> None:
    atomic_write_text(path, text.rstrip())


def read_action_experience_digest_json(path: Path, default: Any = None) -> Any:
    return read_json(path, default)


def write_action_experience_digest_json(path: Path, data: Any) -> None:
    atomic_write_json(path, data, sort_keys=False, indent=2)


def read_action_experience_digest_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in read_text_safe(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def append_action_experience_digest_jsonl(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row, sort_keys=False)
