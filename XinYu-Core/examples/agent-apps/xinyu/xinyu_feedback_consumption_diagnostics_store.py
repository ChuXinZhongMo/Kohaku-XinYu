from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xinyu_state_io import read_text
from xinyu_state_io import write_text
from xinyu_state_io import write_text_atomic


INTENTION_TRACE_REL = Path("runtime/intention_ecology_trace.jsonl")
INTENTION_STATE_REL = Path("memory/context/intention_ecology_state.md")
STATE_REL = Path("memory/context/feedback_consumption_diagnostics_state.md")
TRACE_REL = Path("runtime/feedback_consumption_diagnostics_trace.jsonl")
REPORT_REL = Path("worklog/xinyu-feedback-consumption-diagnostics-latest.md")


def feedback_consumption_intention_trace_path(root: Path) -> Path:
    return Path(root).resolve() / INTENTION_TRACE_REL


def feedback_consumption_intention_state_path(root: Path) -> Path:
    return Path(root).resolve() / INTENTION_STATE_REL


def feedback_consumption_state_path(root: Path) -> Path:
    return Path(root).resolve() / STATE_REL


def feedback_consumption_trace_path(root: Path) -> Path:
    return Path(root).resolve() / TRACE_REL


def read_feedback_consumption_jsonl_tail(path: Path, *, max_lines: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-max(1, int(max_lines)) :]:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def read_feedback_consumption_state_text(root: Path) -> str:
    return read_text(feedback_consumption_intention_state_path(root))


def feedback_consumption_report_path(root: Path, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def write_feedback_consumption_report_text(root: Path, text: str, *, output: Path | None = None) -> Path:
    path = feedback_consumption_report_path(root, output)
    write_text(path, text)
    return path


def write_feedback_consumption_state_text(root: Path, text: str) -> Path:
    path = feedback_consumption_state_path(root)
    write_text_atomic(path, text)
    return path


def append_feedback_consumption_trace_event(root: Path, row: dict[str, Any]) -> Path:
    path = feedback_consumption_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path
