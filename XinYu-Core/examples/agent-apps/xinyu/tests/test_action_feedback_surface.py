from __future__ import annotations

import json
from pathlib import Path

from xinyu_action_feedback_surface import build_action_feedback_prompt_block
from xinyu_action_feedback_surface import read_action_feedback_state
from xinyu_action_feedback_surface import record_action_feedback_from_message_ack
from xinyu_action_feedback_surface import record_action_feedback_from_message_drop
from xinyu_action_feedback_surface import record_action_feedback_from_live_report


def test_message_ack_records_action_feedback_without_visible_text(tmp_path: Path) -> None:
    result = record_action_feedback_from_message_ack(
        tmp_path,
        {
            "route": "chat",
            "message_type": "private",
            "source_message_id": "source-1",
            "adapter_message_id": "adapter-1",
            "turn_id": "turn-1",
            "visible_text": "must not be retained",
        },
        ack_result={"accepted": True, "indexed": True},
        checked_at="2026-05-27T15:00:00+08:00",
    )

    state_text = (tmp_path / "memory/context/action_feedback_state.md").read_text(encoding="utf-8")
    fields = read_action_feedback_state(tmp_path)
    prompt_block = build_action_feedback_prompt_block(tmp_path)
    trace = json.loads((tmp_path / "runtime/action_feedback_trace.jsonl").read_text(encoding="utf-8").splitlines()[0])

    assert result["recorded"] is True
    assert fields["feedback_signal"] == "qq_visible_reply_ack"
    assert fields["action_result"] == "delivered"
    assert fields["future_effect"] == "confirm_visible_reply_transport_for_next_turn"
    assert "must not be retained" not in state_text
    assert "must not be retained" not in prompt_block
    assert trace["raw_private_body_retained"] is False


def test_message_drop_records_stale_reply_feedback_boundary(tmp_path: Path) -> None:
    record_action_feedback_from_message_drop(
        tmp_path,
        {
            "route": "chat",
            "message_type": "private",
            "source_message_id": "source-1",
            "visible_text": "must not be retained",
            "drop_reason": "newer_input_before_visible_send:1->2",
        },
        drop_result={"archive_deleted": True, "tail_removed": True},
        checked_at="2026-05-27T15:01:00+08:00",
    )

    fields = read_action_feedback_state(tmp_path)
    state_text = (tmp_path / "memory/context/action_feedback_state.md").read_text(encoding="utf-8")

    assert fields["feedback_signal"] == "qq_stale_reply_drop"
    assert fields["action_result"] == "unsent_retracted"
    assert fields["future_effect"] == "prefer_latest_owner_input_and_suppress_stale_reply_memory"
    assert fields["stable_memory_write"] == "blocked"
    assert "must not be retained" not in state_text


def test_live_report_backfill_prefers_matching_ack_over_old_stale_drop(tmp_path: Path) -> None:
    result = record_action_feedback_from_live_report(
        tmp_path,
        {
            "checks": [
                {"name": "qq_ack", "ok": False},
                {"name": "stale_reply_drop_guard", "ok": True},
            ],
            "evidence": {
                "latest_private_input": {
                    "present": True,
                    "message_id": "11***11",
                    "recorded_at": "2026-05-27T14:40:00+08:00",
                },
                "latest_reply_sent": {
                    "present": True,
                    "message_id": "11***11",
                    "recorded_at": "2026-05-27T14:40:20+08:00",
                },
                "latest_chat_ack": {
                    "present": True,
                    "route": "chat",
                    "message_type": "private",
                    "source_message_id": "11***11",
                    "adapter_message_id": "22***22",
                    "acked_at": "2026-05-27T14:40:21+08:00",
                },
                "latest_stale_reply_drop": {
                    "present": True,
                    "message_id": "00***00",
                    "message_kind": "private",
                    "recorded_at": "2026-05-27T14:30:00+08:00",
                },
            },
        },
        checked_at="2026-05-27T17:00:00+08:00",
    )

    fields = read_action_feedback_state(tmp_path)

    assert result["feedback_signal"] == "qq_visible_reply_ack"
    assert fields["feedback_signal"] == "qq_visible_reply_ack"
    assert fields["action_result"] == "delivered"
