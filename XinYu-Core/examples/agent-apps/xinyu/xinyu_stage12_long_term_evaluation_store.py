from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xinyu_state_io import write_text_atomic


REPORT_REL = Path("worklog") / "xinyu-stage12-long-term-evaluation-latest.md"
STATE_REL = Path("memory/context/stage12_long_term_evaluation_state.md")
TRACE_REL = Path("runtime/stage12_long_term_evaluation_trace.jsonl")


def stage12_long_term_evaluation_report_path(root: Path | str, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def stage12_long_term_evaluation_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STATE_REL


def stage12_long_term_evaluation_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / TRACE_REL


def write_stage12_long_term_evaluation_report_text(
    root: Path | str,
    text: str,
    *,
    output: Path | None = None,
) -> Path:
    path = stage12_long_term_evaluation_report_path(root, output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_stage12_long_term_evaluation_state_text(root: Path | str, text: str) -> Path:
    path = stage12_long_term_evaluation_state_path(root)
    write_text_atomic(path, text)
    return path


def append_stage12_long_term_evaluation_trace_event(root: Path | str, event: dict[str, Any]) -> Path:
    path = stage12_long_term_evaluation_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return path
