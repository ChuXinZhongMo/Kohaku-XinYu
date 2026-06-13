from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PACKET_REL = Path("worklog") / "xinyu-stage8-learning-trial-validation-latest.md"
STATE_REL = Path("memory/context/stage8_learning_trial_validation_state.md")
LEARNING_STATE_REL = Path("memory/self/learning_closed_loop_state.md")
LEARNING_TRACE_REL = Path("runtime/learning_closed_loop_trace.jsonl")


def stage8_learning_trial_validation_packet_path(root: Path | str, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / PACKET_REL
    if not path.is_absolute():
        path = root / path
    return path


def stage8_learning_trial_validation_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STATE_REL


def stage8_learning_trial_validation_learning_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / LEARNING_STATE_REL


def stage8_learning_trial_validation_learning_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / LEARNING_TRACE_REL


def read_stage8_learning_trial_validation_text(path: Path, *, limit: int = 80000) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")[:limit]
    except OSError:
        return ""


def latest_stage8_learning_trial_validation_jsonl_row(
    path: Path,
    *,
    max_lines: int = 300,
) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return {}
    for line in reversed(lines[-max(1, int(max_lines)) :]):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return {}


def write_stage8_learning_trial_validation_packet_text(
    root: Path | str,
    text: str,
    *,
    output: Path | None = None,
) -> Path:
    path = stage8_learning_trial_validation_packet_path(root, output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_stage8_learning_trial_validation_state_text(root: Path | str, text: str) -> Path:
    path = stage8_learning_trial_validation_state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
