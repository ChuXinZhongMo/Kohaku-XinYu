from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPORT_REL = Path("worklog") / "xinyu-stage13-self-narrative-latest.md"
STATE_REL = Path("memory/context/stage13_self_narrative_state.md")
TRACE_REL = Path("runtime/stage13_self_narrative_trace.jsonl")


def stage13_self_narrative_report_path(root: Path | str, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def stage13_self_narrative_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STATE_REL


def stage13_self_narrative_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / TRACE_REL


def write_stage13_self_narrative_report_text(
    root: Path | str,
    text: str,
    *,
    output: Path | None = None,
) -> Path:
    path = stage13_self_narrative_report_path(root, output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_stage13_self_narrative_state_text(root: Path | str, text: str) -> Path:
    path = stage13_self_narrative_state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def append_stage13_self_narrative_trace_event(root: Path | str, event: dict[str, Any]) -> Path:
    path = stage13_self_narrative_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return path
