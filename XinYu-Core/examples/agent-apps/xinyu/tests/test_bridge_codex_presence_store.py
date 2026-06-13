from __future__ import annotations

from pathlib import Path

from xinyu_bridge_codex_presence_store import append_codex_background_trace
from xinyu_bridge_codex_presence_store import read_codex_presence_json


def test_codex_presence_store_reads_json_dict(tmp_path: Path) -> None:
    path = tmp_path / "runtime/codex_presence_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"status":"running","job_id":"codex-1"}', encoding="utf-8-sig")

    assert read_codex_presence_json(path) == {"status": "running", "job_id": "codex-1"}


def test_codex_presence_store_returns_none_for_missing_bad_or_non_dict(tmp_path: Path) -> None:
    path = tmp_path / "runtime/codex_presence_state.json"

    assert read_codex_presence_json(path) is None

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{bad", encoding="utf-8")
    assert read_codex_presence_json(path) is None

    path.write_text('["not", "dict"]', encoding="utf-8")
    assert read_codex_presence_json(path) is None


def test_codex_presence_store_appends_background_trace(tmp_path: Path) -> None:
    path = tmp_path / "memory/knowledge/codex_delegate_background_trace.log"

    assert append_codex_background_trace(path, "one\n") is True
    assert append_codex_background_trace(path, "two\n") is True

    assert path.read_text(encoding="utf-8") == "one\ntwo\n"
