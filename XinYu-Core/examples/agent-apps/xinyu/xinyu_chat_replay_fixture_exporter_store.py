from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from state_service import atomic_write_json
from state_service import atomic_write_text


def chat_replay_path_exists(path: Path) -> bool:
    return path.exists()


def read_chat_replay_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def read_chat_replay_jsonl_file(path: Path) -> list[dict[str, Any]]:
    try:
        lines = read_chat_replay_text(path).splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines:
        clean = line.strip()
        if not clean:
            continue
        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def write_chat_replay_text(path: Path, text: str, *, final_newline: bool = True) -> None:
    atomic_write_text(path, text, final_newline=final_newline)


def write_chat_replay_json(path: Path, data: Any) -> None:
    atomic_write_json(path, data)
