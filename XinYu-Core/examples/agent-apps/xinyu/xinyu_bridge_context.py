from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def prompt_context_signature(xinyu_dir: Path, rel_paths: Iterable[str]) -> str:
    parts: list[str] = []
    for rel in rel_paths:
        path = xinyu_dir / rel
        try:
            stat = path.stat()
        except OSError:
            parts.append(f"{rel}:missing")
            continue
        parts.append(f"{rel}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)
