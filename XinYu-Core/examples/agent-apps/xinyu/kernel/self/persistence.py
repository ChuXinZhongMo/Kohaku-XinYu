"""Persistence helpers for Self (Cognitive Kernel).

Provides memory-based usage + optional JSON file persistence.
No database is used at this stage (K-001).

These functions operate on the public Self interface.
"""

from __future__ import annotations

import json
from pathlib import Path

from .ownership import Self


def save_self_to_json(self_instance: Self, path: Path | str) -> None:
    """Persist a Self instance to a JSON file.

    The file will be overwritten. Creates parent directories if needed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = self_instance.to_dict()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_self_from_json(path: Path | str) -> Self:
    """Load a Self instance from a JSON file.

    Raises FileNotFoundError if the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Self persistence file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return Self.from_dict(data)


def self_to_json_string(self_instance: Self) -> str:
    """Serialize Self to a JSON string (useful for in-memory or network use)."""
    return json.dumps(self_instance.to_dict(), ensure_ascii=False)


def self_from_json_string(data: str) -> Self:
    """Reconstruct Self from a JSON string."""
    return Self.from_dict(json.loads(data))
