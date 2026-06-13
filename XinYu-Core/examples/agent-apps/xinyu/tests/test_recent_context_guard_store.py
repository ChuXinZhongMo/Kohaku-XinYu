from __future__ import annotations

import json

from xinyu_recent_context_guard_store import append_recent_context_guard_trace
from xinyu_recent_context_guard_store import read_recent_context_guard_text
from xinyu_recent_context_guard_store import write_recent_context_guard_text


def test_recent_context_guard_store_reads_text_writes_text_and_appends_trace(tmp_path) -> None:
    recent_path = tmp_path / "memory/context/recent_context.md"
    trace_path = tmp_path / "runtime/recent_context_guard_trace.jsonl"
    recent_path.parent.mkdir(parents=True)
    recent_path.write_bytes(b"\xef\xbb\xbf# Recent Context\n")

    write_recent_context_guard_text(recent_path, "# Recent Context\nbody")
    append_recent_context_guard_trace(trace_path, {"status": "ok", "action": "anchor_synced"})

    assert read_recent_context_guard_text(recent_path) == "# Recent Context\nbody\n"
    assert read_recent_context_guard_text(tmp_path / "missing.md") == ""
    assert [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()] == [
        {"action": "anchor_synced", "status": "ok"}
    ]
