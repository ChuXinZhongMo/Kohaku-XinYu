from __future__ import annotations

from pathlib import Path
from typing import Any

from stores.state_service import atomic_write_json, read_json


BOUNDARY_ID = "stores/sticker_send_state"
COMPATIBILITY_NOTE = "legacy memory/context/sticker_send_state.generated.json physical path kept until callers finish migration"

STICKER_SEND_STATE_REL = Path("memory/context/sticker_send_state.generated.json")


def sticker_send_state_path(root: Path) -> Path:
    return Path(root) / STICKER_SEND_STATE_REL


def read_sticker_send_state(root: Path, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    data = read_json(sticker_send_state_path(root), default=default or {})
    return data if isinstance(data, dict) else dict(default or {})


def write_sticker_send_state(root: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(sticker_send_state_path(root), payload)
