from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text


def write_autonomous_state_text(path: Path, text: str) -> None:
    atomic_write_text(path, text)


def append_autonomous_trace_text(path: Path, line: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
    except Exception:
        return False
    return True
