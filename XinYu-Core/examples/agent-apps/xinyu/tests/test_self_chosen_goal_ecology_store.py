from __future__ import annotations

import json

from xinyu_self_chosen_goal_ecology_store import append_self_chosen_goal_trace
from xinyu_self_chosen_goal_ecology_store import read_self_chosen_goal_json
from xinyu_self_chosen_goal_ecology_store import read_self_chosen_goal_text
from xinyu_self_chosen_goal_ecology_store import write_self_chosen_goal_state_json
from xinyu_self_chosen_goal_ecology_store import write_self_chosen_goal_state_markdown


def test_self_chosen_goal_ecology_store_reads_limited_text_and_writes_state_trace(tmp_path) -> None:
    json_path = tmp_path / "runtime/self_chosen_goal_ecology/state.json"
    md_path = tmp_path / "memory/context/self_chosen_goal_ecology_state.md"
    trace_path = tmp_path / "runtime/self_chosen_goal_ecology/trace.jsonl"
    source_path = tmp_path / "memory/context/recent_context.md"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"\xef\xbb\xbf0123456789")

    write_self_chosen_goal_state_json(json_path, {"version": 1, "goals": {}})
    write_self_chosen_goal_state_markdown(md_path, "# Self-Chosen Goal Ecology State")
    append_self_chosen_goal_trace(trace_path, {"event_kind": "goal_ecology_selected", "selected_goal_id": "quiet"})

    assert read_self_chosen_goal_json(json_path) == {"goals": {}, "version": 1}
    assert read_self_chosen_goal_json(tmp_path / "missing.json") == {}
    assert read_self_chosen_goal_text(source_path, limit=4) == "6789"
    assert read_self_chosen_goal_text(tmp_path / "missing.md", limit=4) == ""
    assert md_path.read_text(encoding="utf-8") == "# Self-Chosen Goal Ecology State\n"
    assert [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()] == [
        {"event_kind": "goal_ecology_selected", "selected_goal_id": "quiet"}
    ]
