from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PACKET_REL = Path("worklog") / "xinyu-stage8-duplicate-consolidation-latest.md"
STATE_REL = Path("memory/context/stage8_duplicate_consolidation_state.md")
APPLY_TRACE_REL = Path("runtime/stage8_duplicate_consolidation_apply_trace.jsonl")


def stage8_duplicate_consolidation_packet_path(root: Path | str, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / PACKET_REL
    if not path.is_absolute():
        path = root / path
    return path


def stage8_duplicate_consolidation_state_path(root: Path | str) -> Path:
    return Path(root).resolve() / STATE_REL


def stage8_duplicate_consolidation_apply_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / APPLY_TRACE_REL


def write_stage8_duplicate_consolidation_packet_text(
    root: Path | str,
    text: str,
    *,
    output: Path | None = None,
) -> Path:
    path = stage8_duplicate_consolidation_packet_path(root, output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_stage8_duplicate_consolidation_state_text(root: Path | str, text: str) -> Path:
    path = stage8_duplicate_consolidation_state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def append_stage8_duplicate_consolidation_apply_trace_event(
    root: Path | str,
    payload: dict[str, Any],
) -> Path:
    path = stage8_duplicate_consolidation_apply_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return path
