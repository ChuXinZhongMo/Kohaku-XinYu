from __future__ import annotations

import json
from pathlib import Path

from xinyu_perception_event_layer import (
    build_perception_event_layer_report,
    read_perception_event_layer_state,
    render_perception_event_layer_report,
    write_perception_event_layer_report,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _seed_multisource_perception(root: Path) -> None:
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
                "text_len": 41,
                "raw_text": "RAW_OWNER_PRIVATE_SHOULD_NOT_RENDER_9317",
            },
            {
                "arrival_seq": 2,
                "message_kind": "group",
                "message_id": "group-1",
                "stage": "dropped",
                "drop_reason": "group_not_allowed",
                "recorded_at": "2026-05-28T20:01:00+08:00",
                "text": "RAW_GROUP_TEXT_SHOULD_NOT_RENDER_7329",
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
                    "visible_text": "RAW_VISIBLE_REPLY_SHOULD_NOT_RENDER_1914",
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
    _write_jsonl(
        runtime / "learning_ocr_trace.jsonl",
        [
            {
                "engine": "windows_ocr",
                "path": "D:\\private\\perception-image.png",
                "recorded_at": "2026-05-28T20:03:30+08:00",
                "returncode": 0,
                "status": "ok",
                "stdout": "RAW_OCR_TEXT_SHOULD_NOT_RENDER_6251",
            }
        ],
    )
    _write_jsonl(
        runtime / "voice_input_trace.jsonl",
        [
            {
                "event_id": "voice-perception-1",
                "recorded_at": "2026-05-28T20:03:40+08:00",
                "status": "transcribed",
                "transcript": "RAW_VOICE_TEXT_SHOULD_NOT_RENDER_8462",
                "confidence": 0.9,
            }
        ],
    )
    _write(
        context / "proactive_request_state.md",
        """
        - status: dry_run
        - checked_at: 2026-05-28T20:04:00+08:00
        - request_id: desktop-1
        - request_answer_state: not_requested
        - last_ack_status: dry_run
        - candidate_message: RAW_DESKTOP_TEXT_SHOULD_NOT_RENDER_5510
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
        context / "self_action_patch_executor_state.md",
        """
        - checked_at: 2026-05-28T20:06:00+08:00
        - status: prepared
        - execution_level: prepare
        - task_id: patch-task-1
        - codex_status: not_requested
        """,
    )
    _write(
        context / "code_change_awareness_state.md",
        """
        - updated_at: 2026-05-28T20:07:00+08:00
        - status: source_changed
        - source_changed: true
        - bridge_restart_required: false
        - runtime_restart_required: false
        - gateway_restart_may_be_needed: false
        - current_project_digest: digest-1
        """,
    )
    _write(
        context / "runtime_self_presence.md",
        """
        - updated_at: 2026-05-28T20:08:00+08:00
        - bridge_process: running
        - current_turn_state: idle
        - last_turn_status: ok
        - last_turn_at: 2026-05-28T20:08:00+08:00
        """,
    )


def test_perception_event_layer_unifies_sources_without_private_text(tmp_path: Path) -> None:
    _seed_multisource_perception(tmp_path)

    report = build_perception_event_layer_report(tmp_path, generated_at="2026-05-28T20:09:00+08:00")
    output = render_perception_event_layer_report(report)
    write_perception_event_layer_report(tmp_path, report)
    state = read_perception_event_layer_state(tmp_path)
    trace = (tmp_path / "runtime/perception_event_layer_trace.jsonl").read_text(encoding="utf-8")

    event_types = {event["event_type"] for event in report["events"]}
    assert report["status"] == "pass"
    assert report["metrics"]["input_event_count"] == 1
    assert report["metrics"]["qq_event_count"] >= 3
    assert report["metrics"]["desktop_event_count"] >= 1
    assert report["metrics"]["tool_result_event_count"] >= 1
    assert report["metrics"]["system_health_event_count"] >= 1
    assert report["metrics"]["file_change_event_count"] >= 1
    assert report["metrics"]["visual_event_count"] >= 1
    assert report["metrics"]["voice_event_count"] >= 1
    assert report["metrics"]["multimodal_event_count"] == (
        report["metrics"]["visual_event_count"] + report["metrics"]["voice_event_count"]
    )
    assert report["metrics"]["sensory_event_count"] == report["metrics"]["multimodal_event_count"]
    assert report["metrics"]["importance_ready_count"] == report["metrics"]["event_count"]
    assert report["metrics"]["anomaly_count"] >= 1
    assert {
        "owner_text_input",
        "qq_ack",
        "qq_drop",
        "qq_group_boundary",
        "desktop_ack",
        "visual_observation_result",
        "voice_input_result",
    }.issubset(event_types)
    assert state["status"] == "pass"
    assert state["raw_private_body_retained"] == "false"

    leaked = "\n".join(
        [
            "RAW_OWNER_PRIVATE_SHOULD_NOT_RENDER_9317",
            "RAW_GROUP_TEXT_SHOULD_NOT_RENDER_7329",
            "RAW_VISIBLE_REPLY_SHOULD_NOT_RENDER_1914",
            "RAW_DESKTOP_TEXT_SHOULD_NOT_RENDER_5510",
            "RAW_OCR_TEXT_SHOULD_NOT_RENDER_6251",
            "RAW_VOICE_TEXT_SHOULD_NOT_RENDER_8462",
        ]
    )
    for marker in leaked.splitlines():
        assert marker not in output
        assert marker not in trace


def test_perception_events_have_required_stage3_fields(tmp_path: Path) -> None:
    _seed_multisource_perception(tmp_path)

    report = build_perception_event_layer_report(tmp_path, generated_at="2026-05-28T20:09:00+08:00")

    for event in report["events"]:
        assert event["source"]
        assert event["observed_at"]
        assert event["confidence"] in {"low", "medium", "high"}
        assert event["privacy_scope"]
        assert event["evidence_ref"]
        assert event["importance"] in {"low", "normal", "high", "boundary"}
        assert isinstance(event["anomaly"], bool)


def test_perception_event_layer_partial_when_only_owner_input_exists(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "private-only",
                "stage": "coalesced_wait",
                "recorded_at": "2026-05-28T20:00:00+08:00",
                "text_len": 4,
                "raw_text": "RAW_OWNER_PRIVATE_SHOULD_NOT_RENDER_4228",
            }
        ],
    )

    report = build_perception_event_layer_report(tmp_path, generated_at="2026-05-28T20:01:00+08:00")
    output = render_perception_event_layer_report(report)

    assert report["ok"] is True
    assert report["status"] == "partial"
    assert report["metrics"]["event_count"] == 1
    assert report["metrics"]["input_event_count"] == 1
    assert report["metrics"]["visual_event_count"] == 0
    assert report["metrics"]["voice_event_count"] == 0
    assert report["metrics"]["multimodal_event_count"] == 0
    assert report["metrics"]["sensory_event_count"] == 0
    assert "RAW_OWNER_PRIVATE_SHOULD_NOT_RENDER_4228" not in output


def test_perception_event_layer_turns_qq_voice_payload_hint_into_voice_event(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "voice-payload-1",
                "stage": "queued",
                "recorded_at": "2026-05-28T20:00:00+08:00",
                "text_len": 0,
                "rich_summary": "语音:voice_audio:3s",
                "voice_count": 1,
                "record_count": 1,
                "audio_count": 0,
                "raw_audio_path": "D:\\private\\voice.silk",
            }
        ],
    )

    report = build_perception_event_layer_report(tmp_path, generated_at="2026-05-28T20:01:00+08:00")
    output = render_perception_event_layer_report(report)

    voice_events = [event for event in report["events"] if event["event_type"] == "voice_input_result"]
    assert report["ok"] is True
    assert report["metrics"]["voice_event_count"] == 1
    assert report["metrics"]["sensory_event_count"] == 1
    assert voice_events
    assert voice_events[0]["source"] == "qq_voice"
    assert voice_events[0]["confidence"] == "low"
    assert voice_events[0]["privacy_scope"] == "owner_private"
    assert "raw_audio_retained=false" in voice_events[0]["summary"]
    assert "D:\\private\\voice.silk" not in output


def test_perception_event_layer_uses_generated_time_when_surface_time_missing(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "private-only",
                "stage": "queued",
                "recorded_at": "2026-05-28T20:00:00+08:00",
                "text_len": 4,
            }
        ],
    )
    _write(
        tmp_path / "memory/context/code_change_awareness_state.md",
        """
        - status: clean
        - source_changed: false
        - current_project_digest: digest-without-time
        """,
    )

    report = build_perception_event_layer_report(tmp_path, generated_at="2026-05-28T20:01:00+08:00")
    code_events = [event for event in report["events"] if event["source"] == "code_probe"]

    assert code_events
    assert code_events[0]["observed_at"] == "2026-05-28T20:01:00+08:00"


def test_perception_event_layer_reports_no_events(tmp_path: Path) -> None:
    report = build_perception_event_layer_report(tmp_path, generated_at="2026-05-28T20:01:00+08:00")

    assert report["ok"] is False
    assert report["status"] == "no_events"
    assert report["metrics"]["event_count"] == 0
    assert report["metrics"]["visual_event_count"] == 0
    assert report["metrics"]["voice_event_count"] == 0
    assert report["metrics"]["multimodal_event_count"] == 0
    assert report["metrics"]["sensory_event_count"] == 0
    assert "no_perception_events_observed" in report["notes"]
