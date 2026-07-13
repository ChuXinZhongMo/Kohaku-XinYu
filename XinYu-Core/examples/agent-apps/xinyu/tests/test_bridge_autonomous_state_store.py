from __future__ import annotations

from xinyu_bridge_stores import append_autonomous_trace_text
from xinyu_bridge_stores import write_autonomous_state_text


def test_write_autonomous_state_text_uses_state_service_atomic_text_writer(tmp_path) -> None:
    path = tmp_path / "context/autonomous_mind_loop_state.md"

    write_autonomous_state_text(path, "status: running")

    assert path.read_text(encoding="utf-8") == "status: running\n"
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []


def test_append_autonomous_trace_text_appends(tmp_path) -> None:
    path = tmp_path / "context/autonomous_mind_loop_trace.log"

    assert append_autonomous_trace_text(path, "one\n") is True
    assert append_autonomous_trace_text(path, "two\n") is True

    assert path.read_text(encoding="utf-8") == "one\ntwo\n"
