from __future__ import annotations

import json

from xinyu_code_awareness_store import append_source_change_trace
from xinyu_code_awareness_store import read_code_awareness_state_text
from xinyu_code_awareness_store import read_source_snapshot
from xinyu_code_awareness_store import write_code_awareness_state
from xinyu_code_awareness_store import write_source_snapshot


def test_code_awareness_store_writes_snapshot_trace_and_state(tmp_path) -> None:
    snapshot_path = tmp_path / "runtime/code_awareness/source_snapshot.json"
    trace_path = tmp_path / "runtime/code_awareness/source_change_trace.jsonl"
    state_path = tmp_path / "memory/context/code_change_awareness_state.md"
    snapshot = {"digest": "abc", "files": [{"path": "x.py"}]}

    write_source_snapshot(snapshot_path, snapshot)
    append_source_change_trace(trace_path, {"event_kind": "source_snapshot_changed"})
    write_code_awareness_state(state_path, "status: changed")

    assert read_source_snapshot(snapshot_path) == snapshot
    assert [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()] == [
        {"event_kind": "source_snapshot_changed"}
    ]
    assert read_code_awareness_state_text(state_path) == "status: changed\n"
    assert read_source_snapshot(tmp_path / "missing.json") == {}
    assert read_code_awareness_state_text(tmp_path / "missing.md") == ""
