from __future__ import annotations

import json
from pathlib import Path

from xinyu_action_feedback_surface_store import append_action_feedback_trace
from xinyu_action_feedback_surface_store import read_action_feedback_state_text
from xinyu_action_feedback_surface_store import write_action_feedback_state_text


def test_action_feedback_store_state_text_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "memory/context/action_feedback_state.md"

    assert read_action_feedback_state_text(path) == ""

    write_action_feedback_state_text(path, "# Action Feedback State\n")

    assert path.read_text(encoding="utf-8") == "# Action Feedback State\n"
    assert read_action_feedback_state_text(path) == "# Action Feedback State\n"


def test_action_feedback_store_appends_trace(tmp_path: Path) -> None:
    path = tmp_path / "runtime/action_feedback_trace.jsonl"

    append_action_feedback_trace(
        path,
        {
            "event_id": "actfb-test",
            "feedback_signal": "qq_visible_reply_ack",
            "raw_private_body_retained": False,
        },
    )

    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row["event_id"] == "actfb-test"
    assert row["feedback_signal"] == "qq_visible_reply_ack"
    assert row["raw_private_body_retained"] is False
