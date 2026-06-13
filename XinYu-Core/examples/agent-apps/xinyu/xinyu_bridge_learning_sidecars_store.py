from __future__ import annotations

from pathlib import Path


def append_codex_learning_followup_trace(path: Path, line: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
    except Exception:
        return False
    return True
