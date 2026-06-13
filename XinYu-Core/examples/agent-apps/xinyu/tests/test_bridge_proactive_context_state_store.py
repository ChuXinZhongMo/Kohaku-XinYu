from __future__ import annotations

from xinyu_bridge_proactive_context_state_store import write_proactive_request_state_text


def test_write_proactive_request_state_text_preserves_final_newline_option(tmp_path) -> None:
    path = tmp_path / "memory/context/proactive_request_state.md"

    write_proactive_request_state_text(path, "status: answered", final_newline=False)

    assert path.read_text(encoding="utf-8") == "status: answered"
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []
