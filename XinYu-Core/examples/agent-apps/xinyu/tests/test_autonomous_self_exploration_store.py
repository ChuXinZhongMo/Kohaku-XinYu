from __future__ import annotations

from pathlib import Path

from xinyu_autonomous_self_exploration_store import append_autonomous_self_exploration_trace
from xinyu_autonomous_self_exploration_store import read_autonomous_self_exploration_text
from xinyu_autonomous_self_exploration_store import read_autonomous_self_exploration_trace_rows
from xinyu_autonomous_self_exploration_store import write_autonomous_self_exploration_text


def test_autonomous_self_exploration_store_text_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "memory/context/autonomous_self_exploration_state.md"

    assert read_autonomous_self_exploration_text(path) == ""

    write_autonomous_self_exploration_text(path, "state\n")

    assert path.read_text(encoding="utf-8") == "state\n"
    assert read_autonomous_self_exploration_text(path) == "state\n"


def test_autonomous_self_exploration_store_trace_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "runtime/autonomous_self_exploration_trace.jsonl"

    append_autonomous_self_exploration_trace(
        path,
        {
            "event_kind": "autonomous_self_exploration",
            "evaluated_at": "2026-06-01T10:00:00+08:00",
            "research_execution_level": "state_only",
        },
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{bad json\n")

    rows = read_autonomous_self_exploration_trace_rows(path)

    assert len(rows) == 1
    assert rows[0]["event_kind"] == "autonomous_self_exploration"
    assert rows[0]["research_execution_level"] == "state_only"
