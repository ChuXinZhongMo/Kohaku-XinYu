from __future__ import annotations

import json
from pathlib import Path

from xinyu_async_exploration_store import append_async_exploration_jsonl
from xinyu_async_exploration_store import read_async_exploration_report_text
from xinyu_async_exploration_store import read_async_exploration_text
from xinyu_async_exploration_store import write_async_exploration_text


def test_async_exploration_store_text_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "memory/context/async_exploration_state.md"

    assert read_async_exploration_text(path) == ""

    write_async_exploration_text(path, "state\n")

    assert path.read_text(encoding="utf-8") == "state\n"
    assert read_async_exploration_text(path) == "state\n"


def test_async_exploration_store_report_text_status(tmp_path: Path) -> None:
    missing = tmp_path / "missing.md"
    report = tmp_path / "report.md"

    assert read_async_exploration_report_text(missing) == ("missing_report", "")

    report.write_text("# Report\n\n- verified\n", encoding="utf-8")

    assert read_async_exploration_report_text(report) == ("ok", "# Report\n\n- verified\n")


def test_async_exploration_store_appends_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "runtime/async_exploration_trace.jsonl"

    append_async_exploration_jsonl(path, {"event_kind": "created", "resume_id": "wait-1"})

    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row == {"event_kind": "created", "resume_id": "wait-1"}
