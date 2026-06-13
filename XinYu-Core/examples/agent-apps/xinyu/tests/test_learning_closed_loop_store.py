from __future__ import annotations

import json
from pathlib import Path

from xinyu_learning_closed_loop_store import append_learning_closed_loop_trace
from xinyu_learning_closed_loop_store import read_learning_closed_loop_text
from xinyu_learning_closed_loop_store import write_learning_closed_loop_text


def test_learning_closed_loop_store_text_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "memory/self/learning_closed_loop_state.md"

    assert read_learning_closed_loop_text(path) == ""

    write_learning_closed_loop_text(path, "state\n")

    assert path.read_text(encoding="utf-8") == "state\n"
    assert read_learning_closed_loop_text(path) == "state\n"


def test_learning_closed_loop_store_appends_trace(tmp_path: Path) -> None:
    path = tmp_path / "runtime/learning_closed_loop_trace.jsonl"

    append_learning_closed_loop_trace(path, {"event_id": "learnloop-1", "success": True})

    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row == {"event_id": "learnloop-1", "success": True}
