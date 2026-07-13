"""Runtime Self registry for K-009 persistent cognitive subject."""

from __future__ import annotations

from pathlib import Path

from .self import Self
from .self.persistence import load_self_from_json, save_self_to_json

RUNTIME_SELF_ID = "xinyu_runtime_self"


def get_runtime_self_path(root: Path) -> Path:
    return root / "memory" / "kernel" / f"{RUNTIME_SELF_ID}.json"


def get_or_create_runtime_self(root: Path | None = None) -> Self:
    """Load persistent runtime Self or create a fresh one."""
    if root is not None:
        path = get_runtime_self_path(root)
        if path.exists():
            return load_self_from_json(path)
    return Self(self_id=RUNTIME_SELF_ID)


def persist_runtime_self(kernel_self: Self, root: Path) -> None:
    """Persist full kernel state (v2) for long-term continuity."""
    path = get_runtime_self_path(root)
    save_self_to_json(kernel_self, path)