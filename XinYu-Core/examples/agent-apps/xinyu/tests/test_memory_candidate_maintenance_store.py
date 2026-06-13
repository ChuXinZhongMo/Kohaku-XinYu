from __future__ import annotations

import json
from pathlib import Path

from xinyu_memory_candidate_maintenance_store import (
    STATE_REL,
    TRACE_REL,
    append_memory_candidate_maintenance_trace,
    memory_candidate_maintenance_state_path,
    memory_candidate_maintenance_trace_path,
    write_memory_candidate_maintenance_state,
)


def test_memory_candidate_maintenance_store_writes_state_with_single_final_newline(tmp_path: Path) -> None:
    write_memory_candidate_maintenance_state(tmp_path, "# State\n- archived: 1\n\n")

    path = memory_candidate_maintenance_state_path(tmp_path)
    assert path == tmp_path / STATE_REL
    assert path.read_text(encoding="utf-8") == "# State\n- archived: 1\n"


def test_memory_candidate_maintenance_store_appends_trace_jsonl(tmp_path: Path) -> None:
    append_memory_candidate_maintenance_trace(
        tmp_path,
        {"checked_at": "2026-05-22T00:00:00+08:00", "archived": 1, "notes": ["ok"]},
    )

    path = memory_candidate_maintenance_trace_path(tmp_path)
    assert path == tmp_path / TRACE_REL
    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == [
        {"checked_at": "2026-05-22T00:00:00+08:00", "archived": 1, "notes": ["ok"]}
    ]
