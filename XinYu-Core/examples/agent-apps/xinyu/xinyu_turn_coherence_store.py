from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from state_service import atomic_write_text
from state_service import read_text_safe


STATE_MD_REL = Path("memory/context/turn_coherence_state.md")
TRACE_REL = Path("runtime/turn_coherence_trace.jsonl")
MEMORY_BRAID_STATE_REL = Path("memory/context/memory_braid_state.md")
PRIVATE_THOUGHT_STATE_REL = Path("memory/self/private_thought_state.md")
SELF_THOUGHT_STATE_REL = Path("memory/context/self_thought_state.md")
PROACTIVE_REQUEST_STATE_REL = Path("memory/context/proactive_request_state.md")


def turn_coherence_state_path(root: Path) -> Path:
    return Path(root) / STATE_MD_REL


def turn_coherence_trace_path(root: Path) -> Path:
    return Path(root) / TRACE_REL


def turn_coherence_source_path(root: Path, rel_path: str | Path) -> Path:
    return Path(root) / Path(rel_path)


def read_turn_coherence_source_text(root: Path, rel_path: str | Path, *, limit: int) -> str:
    text = read_text_safe(turn_coherence_source_path(root, rel_path), default="").strip()
    if len(text) <= limit:
        return text
    return text[:limit]


def write_turn_coherence_state_text(root: Path, text: str) -> None:
    atomic_write_text(turn_coherence_state_path(root), text.rstrip(), final_newline=True)


def append_turn_coherence_trace_event(root: Path, payload: dict[str, Any]) -> None:
    path = turn_coherence_trace_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
