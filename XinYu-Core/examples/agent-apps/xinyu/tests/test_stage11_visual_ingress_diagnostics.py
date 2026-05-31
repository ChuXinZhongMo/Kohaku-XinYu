from __future__ import annotations

import json
from pathlib import Path

from xinyu_stage11_visual_ingress_diagnostics import (
    append_stage11_visual_ingress_diagnostics_trace,
    build_stage11_visual_ingress_diagnostics,
    render_stage11_visual_ingress_diagnostics,
    write_stage11_visual_ingress_diagnostics_report,
    write_stage11_visual_ingress_diagnostics_state,
)
from xinyu_status import status_fields


RAW_OCR_TEXT = "RAW_STAGE11_VISUAL_OCR_TEXT_SHOULD_NOT_SURFACE_4412"
RAW_IMAGE_PATH = "D:\\private\\owner-image.png"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_visual_ingress_waits_when_visual_fields_are_present_but_zero(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 1,
                "message_kind": "private",
                "message_id": "text-1",
                "stage": "queued",
                "recorded_at": "2026-05-31T00:01:00+08:00",
                "text_len": 3,
                "image_count": 0,
                "sticker_count": 0,
            }
        ],
    )

    report = build_stage11_visual_ingress_diagnostics(
        tmp_path,
        generated_at="2026-05-31T00:02:00+08:00",
    )
    rendered = render_stage11_visual_ingress_diagnostics(report)

    assert report["status"] == "waiting_for_live_visual_payload"
    assert report["model"]["visual_count_field_row_count"] == 1
    assert report["model"]["visual_payload_row_count"] == 0
    assert report["model"]["next_step"] == "send_or_capture_real_private_qq_image_message"
    assert "visual_payload_row_count: 0" in rendered


def test_visual_ingress_detects_qq_visual_payload_hint_without_raw_path(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 2,
                "message_kind": "private",
                "message_id": "image-1",
                "stage": "queued",
                "recorded_at": "2026-05-31T00:03:00+08:00",
                "text_len": 0,
                "image_count": 1,
                "raw_image_path": RAW_IMAGE_PATH,
            }
        ],
    )

    report = build_stage11_visual_ingress_diagnostics(
        tmp_path,
        generated_at="2026-05-31T00:04:00+08:00",
    )
    rendered = render_stage11_visual_ingress_diagnostics(report)

    assert report["status"] == "connected_payload_only"
    assert report["model"]["visual_payload_row_count"] == 1
    assert report["model"]["evidence_mode"] == "qq_visual_payload_hint"
    assert RAW_IMAGE_PATH not in json.dumps(report, ensure_ascii=False)
    assert RAW_IMAGE_PATH not in rendered


def test_visual_ingress_prefers_image_context_vision_summary(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/qq_rich_context_trace.jsonl",
        [
            {
                "arrival_seq": 3,
                "message_kind": "private",
                "message_id": "image-2",
                "stage": "prepared",
                "recorded_at": "2026-05-31T00:05:00+08:00",
                "qq_image_count": 1,
                "qq_image_context_available": True,
                "qq_image_ocr_chars": 0,
                "qq_image_vision_chars": 18,
                "qq_image_context_notes": ["vision_summary_ready"],
            }
        ],
    )

    report = build_stage11_visual_ingress_diagnostics(
        tmp_path,
        generated_at="2026-05-31T00:06:00+08:00",
    )
    rendered = render_stage11_visual_ingress_diagnostics(report)

    assert report["status"] == "connected_interpreted"
    assert report["model"]["image_context_available_count"] == 1
    assert report["model"]["image_context_vision_result_count"] == 1
    assert report["model"]["evidence_mode"] == "image_context_vision_summary"
    assert "image_context_vision_result_count: 1" in rendered


def test_visual_ingress_detects_ocr_trace_without_leaking_text_or_path(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/learning_ocr_trace.jsonl",
        [
            {
                "engine": "windows_ocr",
                "path": RAW_IMAGE_PATH,
                "recorded_at": "2026-05-31T00:07:00+08:00",
                "returncode": 0,
                "status": "ok",
                "stdout": RAW_OCR_TEXT,
            }
        ],
    )

    report = build_stage11_visual_ingress_diagnostics(
        tmp_path,
        generated_at="2026-05-31T00:08:00+08:00",
    )
    rendered = render_stage11_visual_ingress_diagnostics(report)
    report_path = write_stage11_visual_ingress_diagnostics_report(tmp_path, report)
    state_path = write_stage11_visual_ingress_diagnostics_state(tmp_path, report, report_path=report_path)
    trace_path = append_stage11_visual_ingress_diagnostics_trace(tmp_path, report)

    assert report["status"] == "connected_interpreted"
    assert report["model"]["ocr_result_count"] == 1
    assert report["model"]["latest_ocr_text_len"] == len(RAW_OCR_TEXT)
    assert report["model"]["evidence_mode"] == "ocr_trace"
    for text in (
        json.dumps(report, ensure_ascii=False),
        rendered,
        report_path.read_text(encoding="utf-8"),
        state_path.read_text(encoding="utf-8"),
        trace_path.read_text(encoding="utf-8"),
    ):
        assert RAW_OCR_TEXT not in text
        assert RAW_IMAGE_PATH not in text


def test_status_fields_exposes_stage11_visual_ingress(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 4,
                "message_kind": "private",
                "message_id": "text-2",
                "stage": "queued",
                "recorded_at": "2026-05-31T00:09:00+08:00",
                "text_len": 2,
                "image_count": 0,
                "sticker_count": 0,
            }
        ],
    )

    fields = status_fields(tmp_path)

    assert fields["stage11_visual_ingress_status"] == "waiting_for_live_visual_payload"
    assert fields["stage11_visual_count_field_row_count"] == "1"
    assert fields["stage11_visual_payload_row_count"] == "0"
    assert fields["stage11_visual_ingress_next_step"] == "send_or_capture_real_private_qq_image_message"
