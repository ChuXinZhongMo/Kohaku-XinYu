from __future__ import annotations

import json
from pathlib import Path

from xinyu_continuity_handoff_store import append_continuity_handoff_trace
from xinyu_continuity_handoff_store import read_continuity_handoff_text
from xinyu_continuity_handoff_store import write_continuity_handoff_text


def test_continuity_handoff_store_text_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "memory/context/continuity_handoff_state.md"

    assert read_continuity_handoff_text(path) == ""

    write_continuity_handoff_text(path, "state\n")

    assert path.read_text(encoding="utf-8") == "state\n"
    assert read_continuity_handoff_text(path) == "state\n"


def test_continuity_handoff_store_appends_trace(tmp_path: Path) -> None:
    path = tmp_path / "runtime/continuity_handoff_trace.jsonl"

    append_continuity_handoff_trace(path, {"handoff_id": "handoff-1", "open_loop_count": 1})

    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row == {"handoff_id": "handoff-1", "open_loop_count": 1}
