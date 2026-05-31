from __future__ import annotations

import json
from pathlib import Path

from xinyu_stage11_multisensory_extension import (
    TRACE_REL,
    append_stage11_multisensory_extension_trace,
    build_stage11_multisensory_extension,
    render_stage11_multisensory_extension,
    write_stage11_multisensory_extension_report,
    write_stage11_multisensory_extension_state,
)
from xinyu_status import status_fields


RAW_PRIVATE = "RAW_STAGE11_PRIVATE_BODY_SHOULD_NOT_SURFACE_8314"
RAW_OCR = "RAW_OCR_TEXT_SHOULD_NOT_SURFACE_6291"
RAW_VOICE = "RAW_VOICE_TRANSCRIPT_SHOULD_NOT_SURFACE_7725"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _write_ready_stage10_sources(root: Path) -> None:
    _write(
        root / "memory/context/stage8_memory_governance_state.md",
        """# Stage 8 Memory Governance State

- stage8_memory_governance_status: active_guarded
- stage8_memory_ready_for_stage9: true
- stage8_stable_profile_write: blocked_review_only_not_auto_apply
- stage8_owner_memory_write: blocked_owner_review_required
- stage8_stable_identity_profile_apply: blocked
""",
    )
    _write(
        root / "memory/context/runtime_self_presence.md",
        f"""# Runtime Self Presence

- current_turn_state: finished
- last_turn_status: ok
- last_source: owner_private
- last_user_preview: {RAW_PRIVATE}
- last_reply_preview: {RAW_PRIVATE}
""",
    )
    _write(
        root / "memory/context/intention_ecology_state.md",
        """# Intention Ecology State

- selected_intent: hold_presence
- selected_gate: hold_private
- action_level: state_only
- proactive_delivery: review_gated
- review_gated_future_count: 1
""",
    )
    _write(
        root / "memory/context/action_feedback_coverage_state.md",
        """# Action Feedback Coverage State

- latest_feedback_signal: local_probe_success
- latest_feedback_surface: local_tool
- latest_lifecycle_status: succeeded
""",
    )
    _write(
        root / "memory/context/owner_feedback_effect_state.md",
        """# Owner Feedback Effect State

- status: supported
- latest_feedback_kind: explicit_success
- owner_reaction: explicit_success
- future_effect: keep_supported_trial_without_promoting_stable_personality
""",
    )
    _write(
        root / "memory/context/self_action_gateway_state.md",
        """# Self Action Gateway State

- pending_approval_count: 0
- approved_waiting_execution_count: 0
""",
    )
    _write(
        root / "memory/context/self_thought_state.md",
        """# Self Thought State

- research_needed: false
- owner_is_right_recipient: false
""",
    )
    _write(
        root / "memory/context/proactive_response_diagnostics_state.md",
        """# Proactive Response Diagnostics State

- delivered_waiting_owner: false
""",
    )
    _write(
        root / "memory/context/self_state_capsule_state.md",
        """# Self State Capsule

- active: true
""",
    )
    _write(root / "memory/context/recent_context.md", "Codex runtime pytest retrieval work remains active.")


def _seed_visual_ocr(root: Path) -> None:
    _write_jsonl(
        root / "runtime/learning_ocr_trace.jsonl",
        [
            {
                "engine": "windows_ocr",
                "path": "D:\\private\\stage11-image.png",
                "recorded_at": "2026-05-29T10:01:00+08:00",
                "returncode": 0,
                "status": "ok",
                "stdout": RAW_OCR,
            }
        ],
    )


def _seed_voice_trace(root: Path) -> None:
    _write_jsonl(
        root / "runtime/voice_input_trace.jsonl",
        [
            {
                "event_id": "voice-1",
                "recorded_at": "2026-05-29T10:02:00+08:00",
                "status": "transcribed",
                "transcript": RAW_VOICE,
                "confidence": 0.91,
            }
        ],
    )


def _seed_qq_voice_payload(root: Path) -> None:
    _write_jsonl(
        root / "runtime/qq_inbound_trace.jsonl",
        [
            {
                "arrival_seq": 12,
                "message_kind": "private",
                "message_id": "qq-voice-1",
                "stage": "queued",
                "recorded_at": "2026-05-29T10:02:00+08:00",
                "text_len": 0,
                "rich_summary": "语音:voice_audio:3s",
                "voice_count": 1,
                "record_count": 1,
                "audio_count": 0,
                "raw_audio_path": "D:\\private\\voice.silk",
            }
        ],
    )


def test_stage11_connects_visual_and_voice_without_raw_private_text(tmp_path: Path) -> None:
    _write_ready_stage10_sources(tmp_path)
    _seed_visual_ocr(tmp_path)
    _seed_voice_trace(tmp_path)

    report = build_stage11_multisensory_extension(tmp_path, generated_at="2026-05-29T10:03:00+08:00")
    rendered = render_stage11_multisensory_extension(report)
    report_path = write_stage11_multisensory_extension_report(tmp_path, report)
    state_path = write_stage11_multisensory_extension_state(tmp_path, report, report_path=report_path)
    trace_path = append_stage11_multisensory_extension_trace(tmp_path, report)
    state = state_path.read_text(encoding="utf-8")
    trace = trace_path.read_text(encoding="utf-8")

    assert report["status"] == "active"
    assert report["ready_for_stage12"] is True
    assert report["model"]["visual_event_count"] >= 1
    assert report["model"]["voice_event_count"] >= 1
    assert report["model"]["sensory_required_field_missing_count"] == 0
    assert report["model"]["sensory_route_status"] == "visual_and_voice_can_influence_internal_gaps"
    assert report["model"]["visual_ingress_status"] == "connected_interpreted"
    assert report["model"]["visual_ingress_ocr_result_count"] == 1
    assert report["model"]["visual_ingress_evidence_mode"] == "ocr_trace"
    assert report["model"]["voice_ingress_status"] == "connected"
    assert report["model"]["fact_boundary"] == "observation_not_fact"
    assert all(report["gate_proof"].values())
    assert report["boundaries"]["qq_message_enqueued"] is False
    assert report["boundaries"]["consciousness_claim"] is False
    assert (tmp_path / TRACE_REL).exists()

    for marker in (RAW_PRIVATE, RAW_OCR, RAW_VOICE):
        assert marker not in json.dumps(report, ensure_ascii=False)
        assert marker not in rendered
        assert marker not in report_path.read_text(encoding="utf-8")
        assert marker not in state
        assert marker not in trace


def test_stage11_accepts_qq_voice_payload_hint_as_bounded_voice_event(tmp_path: Path) -> None:
    _write_ready_stage10_sources(tmp_path)
    _seed_visual_ocr(tmp_path)
    _seed_qq_voice_payload(tmp_path)

    report = build_stage11_multisensory_extension(tmp_path, generated_at="2026-05-29T10:03:00+08:00")
    rendered = render_stage11_multisensory_extension(report)

    assert report["status"] == "active"
    assert report["ready_for_stage12"] is True
    assert report["model"]["visual_event_count"] >= 1
    assert report["model"]["voice_event_count"] == 1
    assert report["model"]["sensory_route_status"] == "visual_and_voice_can_influence_internal_gaps"
    assert "D:\\private\\voice.silk" not in json.dumps(report, ensure_ascii=False)
    assert "D:\\private\\voice.silk" not in rendered


def test_stage11_is_partial_when_only_visual_is_connected(tmp_path: Path) -> None:
    _write_ready_stage10_sources(tmp_path)
    _seed_visual_ocr(tmp_path)

    report = build_stage11_multisensory_extension(tmp_path, generated_at="2026-05-29T10:03:00+08:00")

    assert report["status"] == "active_partial"
    assert report["ready_for_stage12"] is False
    assert report["model"]["visual_event_count"] >= 1
    assert report["model"]["voice_event_count"] == 0
    assert report["model"]["next_step"] == "connect_or_capture_voice_transcript_event"


def test_stage11_waits_for_sensory_events_after_stage10_ready(tmp_path: Path) -> None:
    _write_ready_stage10_sources(tmp_path)

    report = build_stage11_multisensory_extension(tmp_path, generated_at="2026-05-29T10:03:00+08:00")

    assert report["status"] == "active_waiting_for_sensory_events"
    assert report["ready_for_stage12"] is False
    assert report["model"]["sensory_event_count"] == 0
    assert report["model"]["next_step"] == "wait_for_or_inject_visual_or_voice_event_trace"


def test_stage11_waits_for_stage10_even_when_sensory_traces_exist(tmp_path: Path) -> None:
    _seed_visual_ocr(tmp_path)
    _seed_voice_trace(tmp_path)

    report = build_stage11_multisensory_extension(tmp_path, generated_at="2026-05-29T10:03:00+08:00")

    assert report["status"] == "waiting_for_stage10"
    assert report["ready_for_stage12"] is False
    assert report["model"]["next_step"] == "finish_stage10_proactive_life_loop_first"


def test_status_fields_exposes_stage11_multisensory_extension(tmp_path: Path) -> None:
    _write_ready_stage10_sources(tmp_path)
    _seed_visual_ocr(tmp_path)
    _seed_voice_trace(tmp_path)

    fields = status_fields(tmp_path)

    assert fields["stage11_multisensory_extension_status"] == "active"
    assert fields["stage11_ready_for_stage12"] == "true"
    assert int(fields["stage11_visual_event_count"]) >= 1
    assert int(fields["stage11_voice_event_count"]) >= 1
    assert fields["stage11_visual_ingress_status"] == "connected_interpreted"
    assert fields["stage11_visual_ocr_result_count"] == "1"
    assert fields["stage11_fact_boundary"] == "observation_not_fact"
    assert fields["stage11_raw_visual_body_in_state"] == "false"
    assert fields["stage11_raw_voice_transcript_in_state"] == "false"
    assert fields["stage11_qq_message_enqueued"] == "false"
