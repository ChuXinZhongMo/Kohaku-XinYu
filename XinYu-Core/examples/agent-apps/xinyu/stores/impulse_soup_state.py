from __future__ import annotations

from pathlib import Path
from typing import Any

from stores.state_service import atomic_write_json, read_json


BOUNDARY_ID = "stores/impulse_soup_state"
COMPATIBILITY_NOTE = "legacy memory/context/impulse_soup_state.json physical path kept until callers finish migration"

IMPULSE_SOUP_STATE_REL = Path("memory/context/impulse_soup_state.json")


def impulse_soup_state_path(root: Path) -> Path:
    return Path(root) / IMPULSE_SOUP_STATE_REL


def read_impulse_soup_state(root: Path, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    data = read_json(impulse_soup_state_path(root), default=default or {})
    return data if isinstance(data, dict) else dict(default or {})


def write_impulse_soup_state(root: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(impulse_soup_state_path(root), payload)
