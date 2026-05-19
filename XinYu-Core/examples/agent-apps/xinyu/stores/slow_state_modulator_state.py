from __future__ import annotations

from pathlib import Path
from typing import Any

from stores.state_service import atomic_write_json, read_json


BOUNDARY_ID = "stores/slow_state_modulator_state"
COMPATIBILITY_NOTE = "legacy memory/context/slow_state_modulator_state.json physical path kept until callers finish migration"

SLOW_STATE_REL = Path("memory/context/slow_state_modulator_state.json")


def slow_state_modulator_path(root: Path) -> Path:
    return Path(root) / SLOW_STATE_REL


def read_slow_state_payload(root: Path, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    data = read_json(slow_state_modulator_path(root), default=default or {})
    return data if isinstance(data, dict) else dict(default or {})


def write_slow_state_payload(root: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(slow_state_modulator_path(root), payload)
