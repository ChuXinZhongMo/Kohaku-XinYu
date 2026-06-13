from __future__ import annotations

import json

from xinyu_private_ecosystem_journal_store import (
    append_private_ecosystem_journal_event,
    read_private_ecosystem_journal_text,
)


def test_private_ecosystem_journal_store_appends_and_reads_jsonl(tmp_path) -> None:
    path = tmp_path / "runtime/private_ecosystem/autonomy_journal.jsonl"

    assert read_private_ecosystem_journal_text(path) == ""

    append_private_ecosystem_journal_event(path, {"event_kind": "tick_started", "stable_memory_write": False})
    append_private_ecosystem_journal_event(path, {"event_kind": "goal_selected", "goal_id": "g1"})

    rows = [
        json.loads(line)
        for line in read_private_ecosystem_journal_text(path).splitlines()
        if line.strip()
    ]
    assert rows == [
        {"event_kind": "tick_started", "stable_memory_write": False},
        {"event_kind": "goal_selected", "goal_id": "g1"},
    ]
