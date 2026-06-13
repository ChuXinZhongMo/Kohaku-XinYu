from __future__ import annotations

from xinyu_early_visible_segment_store import append_early_visible_segment_shadow_trace
from xinyu_early_visible_segment_store import read_recent_early_visible_segment_shadow_rows
from xinyu_early_visible_segment_store import write_early_visible_segment_shadow_state


def test_early_visible_segment_store_writes_trace_state_and_reads_recent_rows(tmp_path) -> None:
    trace_path = tmp_path / "runtime/early_visible_segment_shadow.jsonl"
    state_path = tmp_path / "memory/context/early_visible_segment_shadow_state.md"

    append_early_visible_segment_shadow_trace(
        trace_path,
        {"event_kind": "other_event", "status": "ignored"},
    )
    append_early_visible_segment_shadow_trace(
        trace_path,
        {"event_kind": "early_visible_segment_shadow", "status": "accepted_shadow", "elapsed_ms": 10},
    )
    append_early_visible_segment_shadow_trace(
        trace_path,
        {"event_kind": "early_visible_segment_shadow", "status": "rejected_shadow", "elapsed_ms": 20},
    )
    write_early_visible_segment_shadow_state(state_path, "status: shadow_observing")

    rows = read_recent_early_visible_segment_shadow_rows(trace_path, max_rows=1)

    assert rows == [{"elapsed_ms": 20, "event_kind": "early_visible_segment_shadow", "status": "rejected_shadow"}]
    assert state_path.read_text(encoding="utf-8") == "status: shadow_observing\n"
    assert read_recent_early_visible_segment_shadow_rows(tmp_path / "missing.jsonl", max_rows=10) == []
    assert read_recent_early_visible_segment_shadow_rows(trace_path, max_rows=0) == []
