from __future__ import annotations

import json

from xinyu_group_shadow_observer import HISTORY_REL
from xinyu_group_shadow_observer import STATE_REL
from xinyu_group_shadow_observer import TRACE_REL
from xinyu_group_shadow_observer import record_group_shadow_observation


def test_group_shadow_observer_records_hashes_history_and_state(tmp_path) -> None:
    result = record_group_shadow_observation(
        tmp_path,
        event={"group_id": "raw-group", "user_id": "raw-user", "message_id": "raw-message"},
        text="AI style question?",
        normalized_text="AI style question?",
        triggered=False,
    )

    trace_text = (tmp_path / TRACE_REL).read_text(encoding="utf-8")
    history_text = (tmp_path / HISTORY_REL).read_text(encoding="utf-8")
    state_text = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    row = json.loads(trace_text.splitlines()[0])

    assert result["recorded"] is True
    assert row["reply_policy"] == "no_reply_shadow_only"
    assert row["stable_memory_write"] == "blocked"
    assert row["owner_relationship_write"] == "blocked"
    assert "raw-group" not in trace_text + history_text + state_text
    assert "raw-user" not in trace_text + history_text + state_text
    assert "raw-message" not in trace_text + history_text + state_text
