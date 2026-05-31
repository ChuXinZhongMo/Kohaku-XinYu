from __future__ import annotations

import json
from pathlib import Path

from xinyu_perception_importance import (
    build_perception_importance_report,
    read_perception_importance_state,
    render_perception_importance_report,
    write_perception_importance_report,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _seed_perception_events(root: Path) -> None:
    runtime = root / "runtime"
    context = root / "memory/context"
    _write_jsonl(
        runtime / "qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "private-1",
                "stage": "queued",
                "recorded_at": "2026-05-28T20:00:00+08:00",
                "text_len": 23,
                "raw_text": "RAW_OWNER_PRIVATE_SHOULD_NOT_RENDER_7711",
            },
            {
                "arrival_seq": 2,
                "message_kind": "group",
                "message_id": "group-1",
                "stage": "dropped",
                "drop_reason": "group_not_allowed",
                "recorded_at": "2026-05-28T20:01:00+08:00",
                "text": "RAW_GROUP_TEXT_SHOULD_NOT_RENDER_9912",
            },
            {
                "arrival_seq": 3,
                "message_kind": "private",
                "message_id": "stale-1",
                "stage": "stale_reply_dropped",
                "drop_reason": "newer_input_before_visible_send",
                "recorded_at": "2026-05-28T20:02:00+08:00",
            },
        ],
    )
    _write_jsonl(
        runtime / "gateway_ack_spool.jsonl",
        [
            {
                "event": "pending",
                "key": "adapter|ack-1|chat",
                "created_at": "2026-05-28T20:03:00+08:00",
                "payload": {
                    "route": "chat",
                    "adapter_message_id": "ack-1",
                    "source_message_id": "private-1",
                    "message_type": "private",
                    "visible_text": "RAW_VISIBLE_REPLY_SHOULD_NOT_RENDER_5408",
                },
            },
            {
                "event": "acked",
                "key": "adapter|ack-1|chat",
                "acked_at": "2026-05-28T20:03:01+08:00",
                "adapter_message_id": "ack-1",
                "route": "chat",
            },
        ],
    )
    _write(
        context / "proactive_request_state.md",
        """
        - status: approved
        - checked_at: 2026-05-28T20:04:00+08:00
        - request_id: desktop-1
        - request_answer_state: approved_qq
        - last_ack_status: approved_qq
        - candidate_message: RAW_DESKTOP_TEXT_SHOULD_NOT_RENDER_1644
        """,
    )
    _write(
        context / "action_feedback_state.md",
        """
        - status: active
        - checked_at: 2026-05-28T20:05:00+08:00
        - event_id: actfb-1
        - feedback_signal: qq_visible_reply_ack
        - action_result: delivered
        - future_effect: confirm_visible_reply_transport_for_next_turn
        """,
    )
    _write(
        context / "code_change_awareness_state.md",
        """
        - updated_at: 2026-05-28T20:06:00+08:00
        - status: source_changed
        - source_changed: true
        - current_project_digest: digest-1
        """,
    )
    _write(
        context / "runtime_self_presence.md",
        """
        - updated_at: 2026-05-28T20:07:00+08:00
        - bridge_process: running
        - current_turn_state: idle
        - last_turn_status: ok
        - last_turn_at: 2026-05-28T20:07:00+08:00
        """,
    )


def test_perception_importance_judges_events_into_internal_gaps_without_private_text(tmp_path: Path) -> None:
    _seed_perception_events(tmp_path)

    report = build_perception_importance_report(tmp_path, generated_at="2026-05-28T20:08:00+08:00")
    output = render_perception_importance_report(report)
    write_perception_importance_report(tmp_path, report)
    state = read_perception_importance_state(tmp_path)
    trace = (tmp_path / "runtime/perception_importance_trace.jsonl").read_text(encoding="utf-8")

    gap_types = {judgment["gap_type"] for judgment in report["judgments"]}
    assert report["status"] == "pass"
    assert report["metrics"]["judged_event_count"] == report["metrics"]["event_count"]
    assert report["metrics"]["owner_attention_count"] == 1
    assert report["metrics"]["repair_gap_count"] >= 1
    assert report["metrics"]["boundary_gap_count"] >= 1
    assert report["metrics"]["action_residue_count"] >= 1
    assert report["metrics"]["maintenance_gap_count"] >= 1
    assert report["metrics"]["high_attention_count"] >= 2
    assert report["metrics"]["max_attention_weight"] >= 85
    assert state["status"] == "pass"
    assert state["raw_private_body_retained"] == "false"
    assert {"owner_attention", "repair_gap", "boundary_gap", "action_residue", "maintenance_gap"}.issubset(gap_types)

    leaked = "\n".join(
        [
            "RAW_OWNER_PRIVATE_SHOULD_NOT_RENDER_7711",
            "RAW_GROUP_TEXT_SHOULD_NOT_RENDER_9912",
            "RAW_VISIBLE_REPLY_SHOULD_NOT_RENDER_5408",
            "RAW_DESKTOP_TEXT_SHOULD_NOT_RENDER_1644",
        ]
    )
    for marker in leaked.splitlines():
        assert marker not in output
        assert marker not in trace


def test_perception_importance_reports_no_events(tmp_path: Path) -> None:
    report = build_perception_importance_report(tmp_path, generated_at="2026-05-28T20:08:00+08:00")

    assert report["ok"] is False
    assert report["status"] == "no_events"
    assert report["metrics"]["event_count"] == 0
    assert report["metrics"]["judged_event_count"] == 0
    assert "no_events_available_for_importance_judgment" in report["notes"]


def test_perception_importance_accepts_partial_low_attention_event(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/runtime_self_presence.md",
        """
        - updated_at: 2026-05-28T20:07:00+08:00
        - bridge_process: running
        - current_turn_state: idle
        - last_turn_status: ok
        """,
    )

    report = build_perception_importance_report(tmp_path, generated_at="2026-05-28T20:08:00+08:00")

    assert report["ok"] is True
    assert report["status"] == "partial"
    assert report["metrics"]["maintenance_gap_count"] == 1
    assert report["metrics"]["high_attention_count"] == 0
