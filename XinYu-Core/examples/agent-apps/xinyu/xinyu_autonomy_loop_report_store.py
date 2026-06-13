from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xinyu_state_io import read_text
from xinyu_state_io import write_text


REPORT_REL = Path("worklog") / "xinyu-autonomy-loop-latest.md"

INTENTION_STATE_REL = Path("memory/context/intention_ecology_state.md")
INTENTION_TRACE_REL = Path("runtime/intention_ecology_trace.jsonl")
ATTENTION_STATE_REL = Path("memory/context/attention_posture_state.md")
RELATION_STATE_REL = Path("memory/context/relation_posture_state.md")
SELF_THOUGHT_STATE_REL = Path("memory/context/self_thought_state.md")
SHORT_TERM_CONTINUITY_STATE_REL = Path("memory/context/short_term_continuity_state.md")


def autonomy_loop_report_path(root: Path, output: Path | None = None) -> Path:
    root = Path(root)
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def autonomy_loop_state_path(root: Path, rel_path: Path) -> Path:
    return Path(root) / rel_path


def autonomy_loop_intention_trace_path(root: Path) -> Path:
    return Path(root) / INTENTION_TRACE_REL


def read_autonomy_loop_state_text(root: Path, rel_path: Path) -> str:
    return read_text(autonomy_loop_state_path(root, rel_path))


def read_latest_intention_trace(root: Path, *, max_lines: int = 200) -> dict[str, Any]:
    path = autonomy_loop_intention_trace_path(root)
    if not path.exists():
        return {}
    latest: dict[str, Any] = {}
    try:
        for line in path.read_text(encoding="utf-8-sig").splitlines()[-max(1, int(max_lines)) :]:
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                latest = row
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return latest


def write_autonomy_loop_report_text(root: Path, text: str, *, output: Path | None = None) -> Path:
    path = autonomy_loop_report_path(root, output)
    write_text(path, text)
    return path
