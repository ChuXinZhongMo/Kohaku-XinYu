from __future__ import annotations

import json
from pathlib import Path

from xinyu_chat_replay_fixture_exporter_store import chat_replay_path_exists
from xinyu_chat_replay_fixture_exporter_store import read_chat_replay_jsonl_file
from xinyu_chat_replay_fixture_exporter_store import read_chat_replay_text
from xinyu_chat_replay_fixture_exporter_store import write_chat_replay_json
from xinyu_chat_replay_fixture_exporter_store import write_chat_replay_text


def test_chat_replay_store_text_roundtrip_and_exists(tmp_path: Path) -> None:
    path = tmp_path / "runtime/replay_candidates/retrieval_replay_candidates.jsonl"

    assert chat_replay_path_exists(path) is False

    write_chat_replay_text(path, "", final_newline=False)

    assert chat_replay_path_exists(path) is True
    assert path.read_text(encoding="utf-8") == ""
    assert read_chat_replay_text(path) == ""


def test_chat_replay_store_json_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "runtime/replay_candidates/chat_replay_export_summary.json"

    write_chat_replay_json(path, {"selected_count": 2, "notes": ["candidate_local_unreviewed"]})

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "notes": ["candidate_local_unreviewed"],
        "selected_count": 2,
    }


def test_chat_replay_store_reads_jsonl_file_and_skips_bad_rows(tmp_path: Path) -> None:
    path = tmp_path / "tests/fixtures/retrieval_replay_cases.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"id":"case-1"}\nnot-json\n["not", "dict"]\n{"id":"case-2"}\n', encoding="utf-8")

    assert read_chat_replay_jsonl_file(path) == [{"id": "case-1"}, {"id": "case-2"}]


def test_chat_replay_store_missing_jsonl_returns_empty(tmp_path: Path) -> None:
    assert read_chat_replay_jsonl_file(tmp_path / "missing.jsonl") == []
