from __future__ import annotations

import json
from pathlib import Path

from xinyu_short_term_continuity_store import (
    STATE_REL,
    TRACE_REL,
    append_short_term_continuity_trace,
    short_term_continuity_state_path,
    short_term_continuity_trace_path,
    write_short_term_continuity_state,
)


def test_short_term_continuity_store_writes_state_text_exactly(tmp_path: Path) -> None:
    text = "# Short Term Continuity State\n- direct_reference: true\n"

    write_short_term_continuity_state(tmp_path, text)

    path = short_term_continuity_state_path(tmp_path)
    assert path == tmp_path / STATE_REL
    assert path.read_text(encoding="utf-8") == text


def test_short_term_continuity_store_appends_compact_trace_jsonl(tmp_path: Path) -> None:
    append_short_term_continuity_trace(
        tmp_path,
        {
            "turn_id": "turn-1",
            "direct_reference": True,
            "notes": ["direct_reference_requested"],
        },
    )

    path = short_term_continuity_trace_path(tmp_path)
    assert path == tmp_path / TRACE_REL
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines == ['{"direct_reference":true,"notes":["direct_reference_requested"],"turn_id":"turn-1"}']
    assert json.loads(lines[0]) == {
        "turn_id": "turn-1",
        "direct_reference": True,
        "notes": ["direct_reference_requested"],
    }
