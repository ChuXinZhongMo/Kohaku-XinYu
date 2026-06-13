from __future__ import annotations

from xinyu_bridge_promise_followup_state_store import write_promise_followup_state_text


def test_write_promise_followup_state_text_uses_state_service_atomic_text_writer(tmp_path) -> None:
    path = tmp_path / "memory/context/promise_followup_state.md"

    write_promise_followup_state_text(path, "status: queued")

    assert path.read_text(encoding="utf-8") == "status: queued\n"
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []
