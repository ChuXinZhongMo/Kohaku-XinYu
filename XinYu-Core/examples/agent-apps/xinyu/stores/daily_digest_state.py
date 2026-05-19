from __future__ import annotations

from pathlib import Path
from typing import Any

from stores.state_service import atomic_write_json, read_json


BOUNDARY_ID = "stores/daily_digest_state"
COMPATIBILITY_NOTE = "legacy memory/context/daily_digest.json physical path kept until callers finish migration"

DIGEST_REL = Path("memory/context/daily_digest.json")


def daily_digest_path(root: Path) -> Path:
    return Path(root) / DIGEST_REL


def read_daily_digest(root: Path, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    data = read_json(daily_digest_path(root), default=default or {})
    return data if isinstance(data, dict) else dict(default or {})


def write_daily_digest(root: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(daily_digest_path(root), payload)
