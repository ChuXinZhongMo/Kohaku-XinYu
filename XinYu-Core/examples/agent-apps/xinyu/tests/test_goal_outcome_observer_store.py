from __future__ import annotations

import json

from xinyu_goal_outcome_observer_store import append_goal_outcome_trace
from xinyu_goal_outcome_observer_store import read_goal_outcome_json
from xinyu_goal_outcome_observer_store import read_goal_outcome_jsonl_rows
from xinyu_goal_outcome_observer_store import read_goal_outcome_jsonl_summary
from xinyu_goal_outcome_observer_store import read_goal_outcome_text
from xinyu_goal_outcome_observer_store import write_goal_outcome_json
from xinyu_goal_outcome_observer_store import write_goal_outcome_text


def test_goal_outcome_observer_store_handles_json_text_and_jsonl(tmp_path) -> None:
    json_path = tmp_path / "runtime/self_chosen_goal_ecology/outcome_observer.json"
    text_path = tmp_path / "memory/context/self_chosen_goal_ecology_state.md"
    trace_path = tmp_path / "runtime/self_chosen_goal_ecology/self_chosen_goal_trace.jsonl"

    write_goal_outcome_json(json_path, {"version": 1, "status": "ok"})
    write_goal_outcome_text(text_path, "# Goal Ecology")
    append_goal_outcome_trace(trace_path, {"event_kind": "goal_ecology_selected", "selected_goal_id": "a"})
    append_goal_outcome_trace(trace_path, {"event_kind": "goal_ecology_outcome_observed", "outcome": "useful"})
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")

    assert read_goal_outcome_json(json_path, default={}) == {"status": "ok", "version": 1}
    assert read_goal_outcome_json(tmp_path / "missing.json", default={"missing": True}) == {"missing": True}
    assert read_goal_outcome_text(text_path) == "# Goal Ecology\n"
    assert read_goal_outcome_text(tmp_path / "missing.md") == ""
    assert read_goal_outcome_jsonl_summary(trace_path) == {
        "last_event_kind": "goal_ecology_outcome_observed",
        "row_count": 3,
    }
    assert read_goal_outcome_jsonl_rows(trace_path, max_rows=1) == [
        {"event_kind": "goal_ecology_outcome_observed", "outcome": "useful"}
    ]
