from __future__ import annotations

import json

from xinyu_qq_visible_send_shadow_store import append_visible_send_shadow_trace
from xinyu_qq_visible_send_shadow_store import read_visible_send_shadow_context_text
from xinyu_qq_visible_send_shadow_store import write_visible_send_shadow_state


def test_qq_visible_send_shadow_store_reads_context_and_writes_trace_state(tmp_path) -> None:
    context_path = tmp_path / "memory/context/contextual_recall_state.md"
    trace_path = tmp_path / "runtime/answer_discipline_visible_send_shadow.jsonl"
    state_path = tmp_path / "memory/context/answer_discipline_visible_send_shadow_state.md"
    context_path.parent.mkdir(parents=True)
    context_path.write_bytes(b"\xef\xbb\xbf- retrieval_pressure: high\n")

    append_visible_send_shadow_trace(trace_path, {"source": "qq_outbox_pre_send", "passed": True})
    write_visible_send_shadow_state(state_path, "- shadow_only: true")

    assert read_visible_send_shadow_context_text(context_path) == "- retrieval_pressure: high\n"
    assert read_visible_send_shadow_context_text(tmp_path / "missing.md") == ""
    assert [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()] == [
        {"passed": True, "source": "qq_outbox_pre_send"}
    ]
    assert state_path.read_text(encoding="utf-8") == "- shadow_only: true\n"
