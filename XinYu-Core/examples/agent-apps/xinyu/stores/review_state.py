from __future__ import annotations

from pathlib import Path
from typing import Any

from stores.state_service import atomic_write_json, read_json


BOUNDARY_ID = "stores/review_state"
COMPATIBILITY_NOTE = "legacy memory/context physical paths kept until callers finish migration"

CURSOR_REL = Path("memory/context/review_inbox_cursor.json")
DECISIONS_REL = Path("memory/context/review_inbox_decisions.json")
LOCK_REL = Path("memory/context/.review_inbox.lock")


def review_cursor_path(root: Path) -> Path:
    return root / CURSOR_REL


def review_decisions_path(root: Path) -> Path:
    return root / DECISIONS_REL


def review_lock_path(root: Path) -> Path:
    return root / LOCK_REL


def read_review_cursor(root: Path, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    data = read_json(review_cursor_path(root), default=default or {})
    return data if isinstance(data, dict) else dict(default or {})


def write_review_cursor(root: Path, data: dict[str, Any]) -> None:
    atomic_write_json(review_cursor_path(root), data)


def read_review_decisions(root: Path, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    data = read_json(review_decisions_path(root), default=default or {})
    return data if isinstance(data, dict) else dict(default or {})


def write_review_decisions(root: Path, data: dict[str, Any]) -> None:
    atomic_write_json(review_decisions_path(root), data)
