from __future__ import annotations

import json
from pathlib import Path

from xinyu_attention_posture_store import read_attention_life_event_trace_rows
from xinyu_attention_posture_store import read_attention_posture_text
from xinyu_attention_posture_store import write_attention_life_event_trace_rows
from xinyu_attention_posture_store import write_attention_posture_text


def test_attention_posture_store_text_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "memory/context/attention_posture_state.md"

    assert read_attention_posture_text(path) == ""

    write_attention_posture_text(path, "state\n")

    assert path.read_text(encoding="utf-8") == "state\n"
    assert read_attention_posture_text(path) == "state\n"


def test_attention_posture_store_trace_rows_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "memory/context/life_event_trace.jsonl"
    rows = [
        {"route": "short_trace", "event_id": "life-1"},
        {"route": "owner_private_question", "event_id": "life-2"},
    ]

    write_attention_life_event_trace_rows(path, rows)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0]) == {"event_id": "life-1", "route": "short_trace"}
    assert read_attention_life_event_trace_rows(path) == rows


def test_attention_posture_store_missing_trace_returns_empty(tmp_path: Path) -> None:
    assert read_attention_life_event_trace_rows(tmp_path / "missing.jsonl") == []
