from __future__ import annotations

import json
from pathlib import Path

from xinyu_autonomous_outward_action_store import append_autonomous_outward_event
from xinyu_autonomous_outward_action_store import read_autonomous_outward_json
from xinyu_autonomous_outward_action_store import read_autonomous_outward_jsonl_rows
from xinyu_autonomous_outward_action_store import read_autonomous_outward_text
from xinyu_autonomous_outward_action_store import write_autonomous_outward_text


def test_autonomous_outward_store_text_and_json(tmp_path: Path) -> None:
    text_path = tmp_path / "memory/context/autonomous_outward_action_state.md"
    json_path = tmp_path / "xinyu_qq_gateway.config.json"

    assert read_autonomous_outward_text(text_path) == ""
    assert read_autonomous_outward_json(json_path, default={}) == {}

    write_autonomous_outward_text(text_path, "state\n")
    json_path.write_text(json.dumps({"owner_user_ids": ["owner-1"]}), encoding="utf-8")

    assert text_path.read_text(encoding="utf-8") == "state\n"
    assert read_autonomous_outward_text(text_path) == "state\n"
    assert read_autonomous_outward_json(json_path, default={}) == {"owner_user_ids": ["owner-1"]}


def test_autonomous_outward_store_jsonl_rows_skip_invalid_and_non_dict(tmp_path: Path) -> None:
    path = tmp_path / "runtime/autonomous_outward_action/ledger.jsonl"

    append_autonomous_outward_event(
        path,
        {
            "event_kind": "autonomous_outward_action",
            "evaluated_at": "2026-06-01T10:00:00+08:00",
            "queued": True,
        },
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write("[1, 2]\n")
        handle.write("{bad json\n")

    rows = read_autonomous_outward_jsonl_rows(path)

    assert len(rows) == 1
    assert rows[0]["event_kind"] == "autonomous_outward_action"
    assert rows[0]["queued"] is True
