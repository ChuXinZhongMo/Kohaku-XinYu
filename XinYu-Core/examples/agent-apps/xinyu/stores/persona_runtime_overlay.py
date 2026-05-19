from __future__ import annotations

from pathlib import Path
from typing import Any

from stores.state_service import atomic_write_json, read_json


BOUNDARY_ID = "stores/persona_runtime_overlay"
COMPATIBILITY_NOTE = "legacy memory/self/goldmark_positive_overlay.json physical path kept until callers finish migration"

OVERLAY_REL = Path("memory/self/goldmark_positive_overlay.json")


def goldmark_overlay_path(root: Path) -> Path:
    return Path(root) / OVERLAY_REL


def read_goldmark_overlay(root: Path, *, default: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    data = read_json(goldmark_overlay_path(root), default=default or [])
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("entries"), list):
        return [item for item in data.get("entries", []) if isinstance(item, dict)]
    return list(default or [])


def write_goldmark_overlay(root: Path, entries: list[dict[str, Any]]) -> None:
    atomic_write_json(goldmark_overlay_path(root), entries, sort_keys=False)
