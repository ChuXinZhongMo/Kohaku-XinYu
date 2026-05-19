from __future__ import annotations

from pathlib import Path

from stores.review_state import (
    BOUNDARY_ID,
    COMPATIBILITY_NOTE,
    CURSOR_REL,
    DECISIONS_REL,
    read_review_cursor,
    read_review_decisions,
    review_cursor_path,
    review_decisions_path,
    write_review_cursor,
    write_review_decisions,
)
from xinyu_review_inbox import CURSOR_REL as REVIEW_INBOX_CURSOR_REL
from xinyu_review_inbox import DECISIONS_REL as REVIEW_INBOX_DECISIONS_REL
from xinyu_review_inbox import REVIEW_STATE_BOUNDARY


def test_review_state_store_keeps_legacy_paths_as_compatibility_boundary(tmp_path: Path) -> None:
    assert BOUNDARY_ID == "stores/review_state"
    assert REVIEW_STATE_BOUNDARY == BOUNDARY_ID
    assert "legacy memory/context" in COMPATIBILITY_NOTE
    assert CURSOR_REL == REVIEW_INBOX_CURSOR_REL
    assert DECISIONS_REL == REVIEW_INBOX_DECISIONS_REL

    write_review_cursor(tmp_path, {"version": 1, "items": [{"index": 1}]})
    write_review_decisions(tmp_path, {"version": 1, "decisions": [{"decision": "accepted"}]})

    assert review_cursor_path(tmp_path) == tmp_path / "memory/context/review_inbox_cursor.json"
    assert review_decisions_path(tmp_path) == tmp_path / "memory/context/review_inbox_decisions.json"
    assert read_review_cursor(tmp_path)["items"][0]["index"] == 1
    assert read_review_decisions(tmp_path)["decisions"][0]["decision"] == "accepted"
