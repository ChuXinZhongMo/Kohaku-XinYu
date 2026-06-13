from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from state_service import atomic_write_text


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def dialogue_working_memory_session_hash(session_key: str) -> str:
    normalized = _safe_str(session_key, "default").strip() or "default"
    return hashlib.sha256(normalized.encode("utf-8", errors="replace")).hexdigest()[:24]


def dialogue_working_memory_session_path(root: Path, session_key: str) -> Path:
    return Path(root) / "runtime/dialogue_working_memory" / f"{dialogue_working_memory_session_hash(session_key)}.jsonl"


def dialogue_working_memory_path_exists(path: Path) -> bool:
    return Path(path).exists()


def read_dialogue_working_memory_raw(path: Path) -> tuple[str, str]:
    try:
        return Path(path).read_text(encoding="utf-8-sig", errors="replace"), ""
    except OSError as exc:
        return "", type(exc).__name__


def read_dialogue_working_memory_rows(path: Path) -> list[dict[str, Any]]:
    raw, error = read_dialogue_working_memory_raw(path)
    if error or not raw:
        return []
    rows: list[dict[str, Any]] = []
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def write_dialogue_working_memory_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    content = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if rows:
        content += "\n"
    atomic_write_text(Path(path), content, final_newline=False)


def clear_dialogue_working_memory_rows(path: Path) -> None:
    atomic_write_text(Path(path), "", final_newline=False)
