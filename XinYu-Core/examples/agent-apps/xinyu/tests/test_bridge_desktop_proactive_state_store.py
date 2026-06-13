from __future__ import annotations

import json

from xinyu_bridge_desktop_proactive_state_store import append_desktop_proactive_history_jsonl
from xinyu_bridge_desktop_proactive_state_store import write_desktop_proactive_request_state_text


def test_append_desktop_proactive_history_jsonl_uses_state_service_jsonl_writer(tmp_path) -> None:
    path = tmp_path / "runtime/desktop/proactive_history.jsonl"

    append_desktop_proactive_history_jsonl(path, {"b": 2, "a": 1})

    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] == [
        {"a": 1, "b": 2}
    ]


def test_write_desktop_proactive_request_state_text_preserves_final_newline_option(tmp_path) -> None:
    path = tmp_path / "memory/context/proactive_request_state.md"

    write_desktop_proactive_request_state_text(path, "status: answered", final_newline=False)

    assert path.read_text(encoding="utf-8") == "status: answered"
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []
