from __future__ import annotations

import json

from xinyu_group_interest_memory_store import append_group_interest_trace
from xinyu_group_interest_memory_store import read_group_interest_state_json
from xinyu_group_interest_memory_store import write_group_interest_state_json
from xinyu_group_interest_memory_store import write_group_interest_state_markdown


def test_group_interest_memory_store_reads_state_and_writes_trace_projection(tmp_path) -> None:
    state_path = tmp_path / "runtime/group_interest/group_interest_state.json"
    trace_path = tmp_path / "runtime/group_interest/group_interest_events.jsonl"
    markdown_path = tmp_path / "memory/context/group_interest_state.md"
    state = {"version": 1, "groups": {"g": {"last_seen_at": "now"}}}

    write_group_interest_state_json(state_path, state)
    append_group_interest_trace(trace_path, {"source": "qq_group_interest_memory", "should_reply": False})
    write_group_interest_state_markdown(markdown_path, "# Group Interest State")

    assert read_group_interest_state_json(state_path) == state
    assert read_group_interest_state_json(tmp_path / "missing.json") == {}
    assert [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()] == [
        {"should_reply": False, "source": "qq_group_interest_memory"}
    ]
    assert markdown_path.read_text(encoding="utf-8") == "# Group Interest State\n"
