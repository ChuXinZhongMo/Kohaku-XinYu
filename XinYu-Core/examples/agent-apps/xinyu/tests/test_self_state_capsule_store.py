from __future__ import annotations

from xinyu_self_state_capsule_store import read_self_state_capsule_context_text
from xinyu_self_state_capsule_store import write_self_state_capsule_state


def test_self_state_capsule_store_reads_context_and_writes_state(tmp_path) -> None:
    context_path = tmp_path / "memory/self/learning_closed_loop_state.md"
    state_path = tmp_path / "memory/context/self_state_capsule_state.md"
    context_path.parent.mkdir(parents=True)
    context_path.write_bytes(b"\xef\xbb\xbf- status: trial_active\n")

    write_self_state_capsule_state(state_path, "- active: true")

    assert read_self_state_capsule_context_text(context_path) == "- status: trial_active\n"
    assert read_self_state_capsule_context_text(tmp_path / "missing.md") == ""
    assert state_path.read_text(encoding="utf-8") == "- active: true\n"
