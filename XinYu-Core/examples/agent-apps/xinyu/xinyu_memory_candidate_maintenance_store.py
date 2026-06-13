from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl
from state_service import atomic_write_text


STATE_REL = Path("memory/context/memory_candidate_maintenance_state.md")
TRACE_REL = Path("runtime/memory_candidate_maintenance_trace.jsonl")


def memory_candidate_maintenance_state_path(root: Path) -> Path:
    return Path(root) / STATE_REL


def memory_candidate_maintenance_trace_path(root: Path) -> Path:
    return Path(root) / TRACE_REL


def write_memory_candidate_maintenance_state(root: Path, text: str) -> None:
    atomic_write_text(memory_candidate_maintenance_state_path(root), text.rstrip(), final_newline=True)


def append_memory_candidate_maintenance_trace(root: Path, payload: dict[str, Any]) -> None:
    append_jsonl(memory_candidate_maintenance_trace_path(root), payload, sort_keys=True)
