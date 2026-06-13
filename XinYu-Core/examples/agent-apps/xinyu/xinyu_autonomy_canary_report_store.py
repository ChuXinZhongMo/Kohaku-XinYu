from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xinyu_state_io import read_text


RELATION_STATE_REL = Path("memory/context/relation_posture_state.md")
INTENTION_STATE_REL = Path("memory/context/intention_ecology_state.md")
INTENTION_TRACE_REL = Path("runtime/intention_ecology_trace.jsonl")


def read_autonomy_canary_text(path: Path) -> str:
    return read_text(path)


def read_autonomy_canary_recent_traces(path: Path, *, limit: int) -> list[dict[str, Any]]:
    text = read_text(path)
    if not text.strip():
        return []
    rows: list[dict[str, Any]] = []
    for line in text.splitlines()[-limit:]:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        rows.append(
            {
                "checked_at": data.get("checked_at", ""),
                "selected_intent": data.get("selected_intent", ""),
                "selected_gate": data.get("selected_gate", ""),
                "autonomy_posture": data.get("autonomy_posture", ""),
                "feedback_signal": data.get("feedback_signal", ""),
                "proactive_candidate": data.get("proactive_candidate", ""),
                "memory_candidate": data.get("memory_candidate", ""),
                "restraint_reason": data.get("restraint_reason", ""),
            }
        )
    return rows
