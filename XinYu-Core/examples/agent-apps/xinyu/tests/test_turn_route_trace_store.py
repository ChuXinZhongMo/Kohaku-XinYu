from __future__ import annotations

import json

from xinyu_turn_route_trace_store import append_turn_route_trace
from xinyu_turn_route_trace_store import read_turn_route_state
from xinyu_turn_route_trace_store import read_turn_route_trace_text
from xinyu_turn_route_trace_store import write_turn_route_state


def test_turn_route_trace_store_writes_jsonl_and_state_json(tmp_path) -> None:
    trace_path = tmp_path / "runtime/turn_route_trace.jsonl"
    state_path = tmp_path / "runtime/turn_route_state.json"
    row = {"turn_id": "turn-1", "stage": "model", "route": "slow_live"}

    append_turn_route_trace(trace_path, row)
    write_turn_route_state(state_path, row)

    assert [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()] == [row]
    assert read_turn_route_state(state_path) == row
    assert read_turn_route_state(tmp_path / "missing.json") == {}


def test_turn_route_trace_store_reads_trace_text_safely(tmp_path) -> None:
    trace_path = tmp_path / "runtime/turn_route_trace.jsonl"
    trace_path.parent.mkdir(parents=True)
    trace_path.write_bytes(b"\xef\xbb\xbf{\"status\":\"timeout\"}\n")

    assert read_turn_route_trace_text(trace_path) == '{"status":"timeout"}\n'
    assert read_turn_route_trace_text(tmp_path / "missing.jsonl") == ""
