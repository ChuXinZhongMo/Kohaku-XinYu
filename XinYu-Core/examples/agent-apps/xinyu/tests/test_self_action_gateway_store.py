from __future__ import annotations

import json

from xinyu_self_action_gateway_store import append_self_action_gateway_trace
from xinyu_self_action_gateway_store import read_self_action_gateway_json
from xinyu_self_action_gateway_store import read_self_action_gateway_jsonl_summary
from xinyu_self_action_gateway_store import read_self_action_gateway_text
from xinyu_self_action_gateway_store import write_self_action_gateway_json
from xinyu_self_action_gateway_store import write_self_action_gateway_text


def test_self_action_gateway_store_reads_limited_text_and_writes_state_trace(tmp_path) -> None:
    json_path = tmp_path / "runtime/self_action_gateway/state.json"
    text_path = tmp_path / "memory/context/self_action_gateway_state.md"
    trace_path = tmp_path / "runtime/self_action_gateway/trace.jsonl"
    handoff_path = tmp_path / "memory/context/self_action_gateway_execution_handoff.md"
    handoff_path.parent.mkdir(parents=True)
    handoff_path.write_bytes(b"\xef\xbb\xbf0123456789")

    write_self_action_gateway_json(json_path, {"version": 1, "status": "active"})
    write_self_action_gateway_text(text_path, "# Self Action Gateway State")
    append_self_action_gateway_trace(trace_path, {"event_kind": "self_action_gateway_run"})
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")

    assert read_self_action_gateway_json(json_path, default={}) == {"status": "active", "version": 1}
    assert read_self_action_gateway_json(tmp_path / "missing.json", default={"missing": True}) == {"missing": True}
    assert read_self_action_gateway_text(handoff_path, limit=4) == "6789"
    assert read_self_action_gateway_text(tmp_path / "missing.md", limit=4) == ""
    assert text_path.read_text(encoding="utf-8") == "# Self Action Gateway State\n"
    assert read_self_action_gateway_jsonl_summary(trace_path) == (2, "self_action_gateway_run")
