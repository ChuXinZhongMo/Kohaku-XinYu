from __future__ import annotations

import json

from xinyu_private_reply_selftest_store import append_private_reply_selftest_trace
from xinyu_private_reply_selftest_store import read_private_reply_selftest_text
from xinyu_private_reply_selftest_store import write_private_reply_selftest_state


def test_private_reply_selftest_store_reads_text_and_writes_state_trace(tmp_path) -> None:
    token_path = tmp_path / ".xinyu_bridge_token"
    state_path = tmp_path / "runtime/private_reply_selftest_state.json"
    trace_path = tmp_path / "runtime/private_reply_selftest_trace.jsonl"
    token_path.write_bytes(b"\xef\xbb\xbftest-token\n")
    state = {"status": "pass", "schema_version": 1}

    write_private_reply_selftest_state(state_path, state)
    append_private_reply_selftest_trace(trace_path, state)

    assert read_private_reply_selftest_text(token_path) == "test-token\n"
    assert read_private_reply_selftest_text(tmp_path / "missing.txt") == ""
    assert json.loads(state_path.read_text(encoding="utf-8")) == state
    assert [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()] == [
        {"schema_version": 1, "status": "pass"}
    ]
