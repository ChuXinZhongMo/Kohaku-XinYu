from __future__ import annotations

from pathlib import Path


def memory_snapshot(memory_root: Path) -> dict[str, tuple[int, int]]:
    if not memory_root.exists():
        return {}

    snapshot: dict[str, tuple[int, int]] = {}
    for path in memory_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        snapshot[path.relative_to(memory_root).as_posix()] = (
            stat.st_mtime_ns,
            stat.st_size,
        )
    return snapshot
