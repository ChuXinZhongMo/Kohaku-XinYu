from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xinyu_state_io import read_text
from xinyu_state_io import write_text_atomic


STATE_REL = Path("memory/context/owner_feedback_effect_state.md")
TRACE_REL = Path("runtime/owner_feedback_effect_trace.jsonl")
REPORT_REL = Path("worklog/xinyu-owner-feedback-effect-latest.md")


def owner_feedback_effect_report_path(root: Path | str, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def owner_feedback_effect_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STATE_REL


def owner_feedback_effect_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / TRACE_REL


def read_owner_feedback_effect_state_text(root: Path | str) -> str:
    return read_text(owner_feedback_effect_state_path(root))


def write_owner_feedback_effect_report_text(
    root: Path | str,
    text: str,
    *,
    output: Path | None = None,
) -> Path:
    path = owner_feedback_effect_report_path(root, output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_owner_feedback_effect_state_text(root: Path | str, text: str) -> Path:
    path = owner_feedback_effect_state_path(root)
    write_text_atomic(path, text)
    return path


def append_owner_feedback_effect_trace_event(root: Path | str, row: dict[str, Any]) -> Path:
    path = owner_feedback_effect_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path
