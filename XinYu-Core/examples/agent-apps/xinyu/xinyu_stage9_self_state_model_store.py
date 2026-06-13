from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from state_service import atomic_write_text
from state_service import read_text_safe


REPORT_REL = Path("worklog") / "xinyu-stage9-self-state-model-latest.md"
STATE_REL = Path("memory/context/stage9_self_state_model_state.md")
TRACE_REL = Path("runtime/stage9_self_state_model_trace.jsonl")

SOURCE_RELS: dict[str, Path] = {
    "stage8": Path("memory/context/stage8_memory_governance_state.md"),
    "runtime": Path("memory/context/runtime_self_presence.md"),
    "intention": Path("memory/context/intention_ecology_state.md"),
    "action_feedback": Path("memory/context/action_feedback_coverage_state.md"),
    "owner_feedback": Path("memory/context/owner_feedback_effect_state.md"),
    "self_action": Path("memory/context/self_action_gateway_state.md"),
    "self_thought": Path("memory/context/self_thought_state.md"),
    "proactive": Path("memory/context/proactive_response_diagnostics_state.md"),
    "continuity": Path("memory/context/short_term_continuity_state.md"),
    "capsule": Path("memory/context/self_state_capsule_state.md"),
}


def stage9_report_path(root: Path, output: Path | None = None) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    return path


def stage9_state_path(root: Path) -> Path:
    return Path(root).resolve() / STATE_REL


def stage9_trace_path(root: Path) -> Path:
    return Path(root).resolve() / TRACE_REL


def stage9_source_path(root: Path, source_id: str) -> Path:
    return Path(root).resolve() / SOURCE_RELS[source_id]


def read_stage9_source_text(root: Path, source_id: str, *, limit: int = 50000) -> str:
    text = read_text_safe(stage9_source_path(root, source_id), default="")
    return text[:limit]


def write_stage9_report_text(root: Path, text: str, *, output: Path | None = None) -> Path:
    path = stage9_report_path(root, output)
    atomic_write_text(path, text, final_newline=False)
    return path


def write_stage9_state_text(root: Path, text: str) -> Path:
    path = stage9_state_path(root)
    atomic_write_text(path, text, final_newline=False)
    return path


def append_stage9_trace_event(root: Path, event: dict[str, Any]) -> Path:
    path = stage9_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return path
