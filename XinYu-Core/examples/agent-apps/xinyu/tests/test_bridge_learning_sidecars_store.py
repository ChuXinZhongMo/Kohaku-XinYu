from __future__ import annotations

from pathlib import Path

from xinyu_bridge_stores import append_codex_learning_followup_trace


def test_codex_learning_followup_trace_appends(tmp_path: Path) -> None:
    path = tmp_path / "memory/knowledge/codex_learning_followup_trace.log"

    assert append_codex_learning_followup_trace(path, "one\n") is True
    assert append_codex_learning_followup_trace(path, "two\n") is True

    assert path.read_text(encoding="utf-8") == "one\ntwo\n"
