from __future__ import annotations

import json
from pathlib import Path

from xinyu_action_feedback_coverage_store import append_action_feedback_coverage_trace
from xinyu_action_feedback_coverage_store import latest_action_feedback_jsonl_row
from xinyu_action_feedback_coverage_store import read_action_feedback_coverage_json
from xinyu_action_feedback_coverage_store import read_action_feedback_coverage_text
from xinyu_action_feedback_coverage_store import write_action_feedback_coverage_text


def test_action_feedback_coverage_store_text_and_json(tmp_path: Path) -> None:
    text_path = tmp_path / "memory/context/action_feedback_coverage_state.md"
    json_path = tmp_path / "runtime/codex_presence_state.json"

    assert read_action_feedback_coverage_text(text_path) == ""
    assert read_action_feedback_coverage_json(json_path) == {}

    write_action_feedback_coverage_text(text_path, "state\n")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps({"status": "finished"}), encoding="utf-8")

    assert text_path.read_text(encoding="utf-8") == "state\n"
    assert read_action_feedback_coverage_text(text_path) == "state\n"
    assert read_action_feedback_coverage_json(json_path) == {"status": "finished"}


def test_action_feedback_coverage_store_trace_and_latest_row(tmp_path: Path) -> None:
    path = tmp_path / "runtime/action_feedback_coverage_trace.jsonl"

    append_action_feedback_coverage_trace(path, {"event_kind": "ignored", "status": "partial"})
    append_action_feedback_coverage_trace(path, {"event_kind": "coverage", "status": "pass"})
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{bad json\n")

    latest = latest_action_feedback_jsonl_row(path, lambda row: row.get("event_kind") == "coverage")

    assert latest == {"event_kind": "coverage", "status": "pass"}
