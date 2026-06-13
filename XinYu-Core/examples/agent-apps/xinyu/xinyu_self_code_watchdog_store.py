from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_json
from state_service import atomic_write_text


def write_self_code_watchdog_text(path: Path, text: str) -> None:
    atomic_write_text(path, text, final_newline=False)


def write_self_code_watchdog_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_json(path, data)


def read_self_code_watchdog_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("snapshot manifest must be a JSON object")
    return data


def append_self_code_watchdog_trace(path: Path, payload: dict[str, Any]) -> None:
    append_jsonl(path, payload)


def read_self_code_watchdog_bytes(path: Path) -> bytes:
    return path.read_bytes()


def write_self_code_watchdog_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def copy_self_code_watchdog_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
