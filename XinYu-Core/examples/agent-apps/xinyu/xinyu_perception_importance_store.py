from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xinyu_state_io import read_text
from xinyu_state_io import write_text_atomic


STATE_REL = Path("memory/context/perception_importance_state.md")
TRACE_REL = Path("runtime/perception_importance_trace.jsonl")
REPORT_REL = Path("worklog/xinyu-perception-importance-latest.md")


def perception_importance_report_path(root: Path, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def perception_importance_state_path(root: Path) -> Path:
    return Path(root).resolve() / STATE_REL


def perception_importance_trace_path(root: Path) -> Path:
    return Path(root).resolve() / TRACE_REL


def read_perception_importance_state_text(root: Path) -> str:
    return read_text(perception_importance_state_path(root))


def write_perception_importance_report_text(root: Path, text: str, *, output: Path | None = None) -> Path:
    path = perception_importance_report_path(root, output)
    write_text_atomic(path, text)
    return path


def write_perception_importance_state_text(root: Path, text: str) -> Path:
    path = perception_importance_state_path(root)
    write_text_atomic(path, text)
    return path


def append_perception_importance_trace_event(root: Path, row: dict[str, Any]) -> Path:
    path = perception_importance_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path
