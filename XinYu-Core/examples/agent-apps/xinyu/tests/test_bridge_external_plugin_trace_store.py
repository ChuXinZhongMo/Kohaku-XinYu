from __future__ import annotations

import json

from xinyu_bridge_stores import append_external_plugin_trace


def test_append_external_plugin_trace_uses_state_service_jsonl_writer(tmp_path) -> None:
    path = tmp_path / "runtime/external_plugin_trace.jsonl"

    append_external_plugin_trace(path, {"plugin_id": "kohaku_terrarium", "ok": True})

    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] == [
        {"ok": True, "plugin_id": "kohaku_terrarium"}
    ]
