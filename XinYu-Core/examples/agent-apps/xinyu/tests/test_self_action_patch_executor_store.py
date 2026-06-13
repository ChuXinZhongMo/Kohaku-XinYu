from __future__ import annotations

import json

from xinyu_self_action_patch_executor_store import append_self_action_patch_executor_trace
from xinyu_self_action_patch_executor_store import read_self_action_patch_executor_json
from xinyu_self_action_patch_executor_store import read_self_action_patch_executor_text
from xinyu_self_action_patch_executor_store import write_self_action_patch_executor_json
from xinyu_self_action_patch_executor_store import write_self_action_patch_executor_text


def test_self_action_patch_executor_store_reads_limited_text_and_writes_state_trace(tmp_path) -> None:
    json_path = tmp_path / "runtime/self_action_patch_executor/state.json"
    text_path = tmp_path / "memory/context/self_action_patch_executor_state.md"
    trace_path = tmp_path / "runtime/self_action_patch_executor/trace.jsonl"
    handoff_path = tmp_path / "memory/context/self_action_gateway_execution_handoff.md"
    handoff_path.parent.mkdir(parents=True)
    handoff_path.write_bytes(b"\xef\xbb\xbf0123456789")

    write_self_action_patch_executor_json(json_path, {"status": "prepared", "version": 1})
    write_self_action_patch_executor_text(text_path, "# Self Action Patch Executor State")
    append_self_action_patch_executor_trace(trace_path, {"event_kind": "self_action_patch_executor_run"})

    assert read_self_action_patch_executor_json(json_path, default={}) == {"status": "prepared", "version": 1}
    assert read_self_action_patch_executor_json(tmp_path / "missing.json", default={"missing": True}) == {"missing": True}
    assert read_self_action_patch_executor_text(handoff_path, limit=4) == "6789"
    assert read_self_action_patch_executor_text(tmp_path / "missing.md", limit=4) == ""
    assert text_path.read_text(encoding="utf-8") == "# Self Action Patch Executor State\n"
    assert [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()] == [
        {"event_kind": "self_action_patch_executor_run"}
    ]
