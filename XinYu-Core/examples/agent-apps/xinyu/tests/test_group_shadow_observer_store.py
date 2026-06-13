from __future__ import annotations

import json

from xinyu_group_shadow_observer_store import append_group_shadow_trace
from xinyu_group_shadow_observer_store import read_group_shadow_history_text
from xinyu_group_shadow_observer_store import write_group_shadow_history_text
from xinyu_group_shadow_observer_store import write_group_shadow_state


def test_group_shadow_observer_store_reads_history_and_writes_trace_state(tmp_path) -> None:
    trace_path = tmp_path / "runtime/group_shadow/group_shadow_observations.jsonl"
    history_path = tmp_path / "runtime/group_shadow/group_shadow_recent_messages.jsonl"
    state_path = tmp_path / "memory/context/group_shadow_state.md"
    history_path.parent.mkdir(parents=True)
    history_path.write_bytes(b"\xef\xbb\xbf{\"group_id_hash\":\"g\"}\n")

    append_group_shadow_trace(trace_path, {"source": "qq_gateway_group_shadow", "triggered": False})
    write_group_shadow_history_text(history_path, '{"group_id_hash":"g"}')
    write_group_shadow_state(state_path, "# Group Shadow State")

    assert read_group_shadow_history_text(history_path) == '{"group_id_hash":"g"}\n'
    assert read_group_shadow_history_text(tmp_path / "missing.jsonl") == ""
    assert [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()] == [
        {"source": "qq_gateway_group_shadow", "triggered": False}
    ]
    assert state_path.read_text(encoding="utf-8") == "# Group Shadow State\n"
