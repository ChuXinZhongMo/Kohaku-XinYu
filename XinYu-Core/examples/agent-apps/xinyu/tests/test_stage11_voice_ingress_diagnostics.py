from __future__ import annotations

import json
from pathlib import Path

from xinyu_stage11_voice_ingress_diagnostics import (
    append_stage11_voice_ingress_diagnostics_trace,
    build_stage11_voice_ingress_diagnostics,
    render_stage11_voice_ingress_diagnostics,
    write_stage11_voice_ingress_diagnostics_report,
    write_stage11_voice_ingress_diagnostics_state,
)
from xinyu_status import status_fields


RAW_TRANSCRIPT = "RAW_STAGE11_VOICE_TRANSCRIPT_SHOULD_NOT_SURFACE_9127"
RAW_AUDIO_PATH = "D:\\private\\owner-voice.silk"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_voice_ingress_waits_when_voice_fields_are_present_but_zero(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "text-1",
                "stage": "queued",
                "recorded_at": "2026-05-30T00:01:00+08:00",
                "text_len": 3,
                "voice_count": 0,
                "record_count": 0,
                "audio_count": 0,
            }
        ],
    )

    report = build_stage11_voice_ingress_diagnostics(
        tmp_path,
        generated_at="2026-05-30T00:02:00+08:00",
    )
    rendered = render_stage11_voice_ingress_diagnostics(report)

    assert report["status"] == "waiting_for_live_voice_payload"
    assert report["model"]["voice_count_field_row_count"] == 1
    assert report["model"]["voice_payload_row_count"] == 0
    assert report["model"]["next_step"] == "send_or_capture_real_private_qq_voice_message"
    assert "voice_payload_row_count: 0" in rendered


def test_voice_ingress_detects_qq_voice_payload_hint_without_raw_audio_path(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 2,
                "message_kind": "private",
                "message_id": "voice-1",
                "stage": "queued",
                "recorded_at": "2026-05-30T00:03:00+08:00",
                "text_len": 0,
                "rich_summary": "\u8bed\u97f3:voice_audio:3s",
                "raw_audio_path": RAW_AUDIO_PATH,
            }
        ],
    )

    report = build_stage11_voice_ingress_diagnostics(
        tmp_path,
        generated_at="2026-05-30T00:04:00+08:00",
    )
    rendered = render_stage11_voice_ingress_diagnostics(report)

    assert report["status"] == "connected"
    assert report["model"]["voice_payload_row_count"] == 1
    assert report["model"]["evidence_mode"] == "qq_voice_payload_hint"
    assert RAW_AUDIO_PATH not in json.dumps(report, ensure_ascii=False)
    assert RAW_AUDIO_PATH not in rendered


def test_voice_ingress_detects_transcript_trace_without_leaking_transcript(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/voice_input_trace.jsonl",
        [
            {
                "event_id": "voice-transcript-1",
                "recorded_at": "2026-05-30T00:05:00+08:00",
                "status": "transcribed",
                "transcript": RAW_TRANSCRIPT,
                "confidence": 0.92,
            }
        ],
    )

    report = build_stage11_voice_ingress_diagnostics(
        tmp_path,
        generated_at="2026-05-30T00:06:00+08:00",
    )
    rendered = render_stage11_voice_ingress_diagnostics(report)
    report_path = write_stage11_voice_ingress_diagnostics_report(tmp_path, report)
    state_path = write_stage11_voice_ingress_diagnostics_state(tmp_path, report, report_path=report_path)
    trace_path = append_stage11_voice_ingress_diagnostics_trace(tmp_path, report)

    assert report["status"] == "connected"
    assert report["model"]["voice_transcript_result_count"] == 1
    assert report["model"]["latest_transcript_len"] == len(RAW_TRANSCRIPT)
    assert report["model"]["evidence_mode"] == "transcript_trace"
    for text in (
        json.dumps(report, ensure_ascii=False),
        rendered,
        report_path.read_text(encoding="utf-8"),
        state_path.read_text(encoding="utf-8"),
        trace_path.read_text(encoding="utf-8"),
    ):
        assert RAW_TRANSCRIPT not in text


def test_voice_ingress_counts_failed_transcript_as_attempt_not_result(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 4,
                "message_kind": "private",
                "message_id": "voice-failed-1",
                "stage": "prepared",
                "recorded_at": "2026-05-30T00:08:00+08:00",
                "text_len": 0,
                "rich_summary": "\u8bed\u97f3:voice_audio:3s",
                "voice_count": 1,
                "record_count": 1,
                "audio_count": 0,
            }
        ],
    )
    _write_jsonl(
        tmp_path / "runtime/voice_input_trace.jsonl",
        [
            {
                "event_id": "voice-failed-1",
                "recorded_at": "2026-05-30T00:08:10+08:00",
                "status": "transcription_unavailable",
                "error": "missing_api_key",
                "transcript": "",
            }
        ],
    )

    report = build_stage11_voice_ingress_diagnostics(
        tmp_path,
        generated_at="2026-05-30T00:09:00+08:00",
    )
    rendered = render_stage11_voice_ingress_diagnostics(report)

    assert report["status"] == "connected"
    assert report["model"]["voice_payload_row_count"] == 1
    assert report["model"]["voice_transcript_attempt_count"] == 1
    assert report["model"]["voice_transcript_result_count"] == 0
    assert report["model"]["voice_transcript_error_count"] == 1
    assert "voice_transcript_attempt_count: 1" in rendered
    assert "missing_api_key" not in rendered


def test_status_fields_exposes_stage11_voice_ingress(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 3,
                "message_kind": "private",
                "message_id": "text-2",
                "stage": "queued",
                "recorded_at": "2026-05-30T00:07:00+08:00",
                "text_len": 2,
                "voice_count": 0,
                "record_count": 0,
                "audio_count": 0,
            }
        ],
    )

    fields = status_fields(tmp_path)

    assert fields["stage11_voice_ingress_status"] == "waiting_for_live_voice_payload"
    assert fields["stage11_voice_count_field_row_count"] == "1"
    assert fields["stage11_voice_payload_row_count"] == "0"
    assert fields["stage11_voice_ingress_next_step"] == "send_or_capture_real_private_qq_voice_message"
