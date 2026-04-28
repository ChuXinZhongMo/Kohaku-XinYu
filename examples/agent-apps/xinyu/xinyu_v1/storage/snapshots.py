"""Rollback snapshot helpers."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SnapshotResult:
    source: str
    target: str
    copied: bool
    reason: str = ""


def snapshot_file(source: Path, snapshot_root: Path, *, label: str) -> SnapshotResult:
    if not source.exists() or not source.is_file():
        return SnapshotResult(str(source), "", False, "source_missing")
    snapshot_root.mkdir(parents=True, exist_ok=True)
    target = snapshot_root / f"{label}-{source.name}"
    shutil.copy2(source, target)
    return SnapshotResult(str(source), str(target), True)

