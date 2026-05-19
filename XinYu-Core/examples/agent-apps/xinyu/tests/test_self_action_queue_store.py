from __future__ import annotations

from pathlib import Path

from stores.self_action_queue import (
    APPROVAL_QUEUE_REL,
    BOUNDARY_ID,
    COMPATIBILITY_NOTE,
    append_approval_queue_event,
    approval_queue_path,
    read_approval_queue_events,
    read_approval_queue_rows,
)
from xinyu_bridge_desktop_snapshot import SELF_ACTION_APPROVAL_QUEUE_REL
from xinyu_self_action_gateway import APPROVAL_QUEUE_REL as GATEWAY_APPROVAL_QUEUE_REL
from xinyu_self_action_gateway import SELF_ACTION_QUEUE_BOUNDARY


def test_self_action_queue_store_keeps_legacy_path_as_compatibility_boundary(tmp_path: Path) -> None:
    assert BOUNDARY_ID == "stores/self_action_queue"
    assert SELF_ACTION_QUEUE_BOUNDARY == BOUNDARY_ID
    assert "legacy memory/context" in COMPATIBILITY_NOTE
    assert APPROVAL_QUEUE_REL == GATEWAY_APPROVAL_QUEUE_REL
    assert APPROVAL_QUEUE_REL == SELF_ACTION_APPROVAL_QUEUE_REL

    append_approval_queue_event(
        tmp_path,
        {
            "event_kind": "self_action_approval_queued",
            "queue_id": "selfaction-approval-test",
            "checked_at": "2026-05-19T10:00:00+08:00",
            "status": "pending_owner_approval",
        },
    )

    assert approval_queue_path(tmp_path) == tmp_path / "memory/context/self_action_gateway_approval_queue.jsonl"
    assert read_approval_queue_rows(tmp_path)[0][0] == 0
    assert read_approval_queue_events(tmp_path)[0]["queue_id"] == "selfaction-approval-test"
    assert read_approval_queue_events(tmp_path)[0]["event_time"] == "2026-05-19T10:00:00+08:00"
    assert read_approval_queue_events(tmp_path, limit=0) == []
