from __future__ import annotations

import os
from pathlib import Path


def read_tinykernel_shadow_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def append_tinykernel_shadow_trace_line(path: Path, line: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
