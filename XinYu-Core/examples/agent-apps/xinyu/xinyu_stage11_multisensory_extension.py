from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_perception_event_layer import build_perception_event_layer_report
from xinyu_perception_importance import build_perception_importance_report, perception_gap_signal
from xinyu_stage10_proactive_life_loop import build_stage10_proactive_life_loop
from xinyu_stage11_visual_ingress_diagnostics import build_stage11_visual_ingress_diagnostics
from xinyu_stage11_voice_ingress_diagnostics import build_stage11_voice_ingress_diagnostics
from xinyu_stage11_multisensory_extension_store import REPORT_REL
from xinyu_stage11_multisensory_extension_store import STATE_REL
from xinyu_stage11_multisensory_extension_store import TRACE_REL
from xinyu_stage11_multisensory_extension_store import append_stage11_multisensory_trace_event
from xinyu_stage11_multisensory_extension_store import stage11_multisensory_report_path
from xinyu_stage11_multisensory_extension_store import write_stage11_multisensory_report_text
from xinyu_stage11_multisensory_extension_store import write_stage11_multisensory_state_text


NONE_VALUES = {"", "none", "unknown", "missing", "null"}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _one_line(value: Any, *, limit: int = 220, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    text = _scrub_sensitive(text)
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def _scrub_sensitive(text: str) -> str:
    text = re.sub(r"(?i)\b(?:authorization|api[_-]?key|token|password|cookie)\s*[:=]\s*[^\s<>'\"]+", "<secret>", text)
    text = re.sub(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)\bsk-[a-z0-9_-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+", "<local_path>", text)
    return text


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _sensory_events(event_layer: dict[str, Any]) -> list[dict[str, Any]]:
    events = event_layer.get("events") if isinstance(event_layer.get("events"), list) else []
    return [
        event
        for event in events
        if isinstance(event, dict) and event.get("event_type") in {"visual_observation_result", "voice_input_result"}
    ]


def _sensory_event_contract(events: list[dict[str, Any]]) -> dict[str, Any]:
    missing_required = 0
    confidence_ready = 0
    privacy_ready = 0
    for event in events:
        required = (
            event.get("source"),
            event.get("observed_at"),
            event.get("confidence"),
            event.get("privacy_scope"),
            event.get("evidence_ref"),
        )
        if any(_one_line(value, default="").lower() in NONE_VALUES for value in required):
            missing_required += 1
        if event.get("confidence") in {"low", "medium", "high"}:
            confidence_ready += 1
        if _one_line(event.get("privacy_scope"), default="").lower() not in NONE_VALUES:
            privacy_ready += 1
    count = len(events)
    return {
        "sensory_event_count": count,
        "sensory_required_field_missing_count": missing_required,
        "sensory_confidence_ready_count": confidence_ready,
        "sensory_privacy_ready_count": privacy_ready,
        "sensory_event_contract_ok": count > 0 and missing_required == 0 and confidence_ready == count and privacy_ready == count,
    }


def _status(*, stage10_ready: bool, visual_count: int, voice_count: int, contract_ok: bool) -> str:
    if not stage10_ready:
        return "waiting_for_stage10"
    if visual_count + voice_count <= 0:
        return "active_waiting_for_sensory_events"
    if not contract_ok:
        return "needs_check"
    if visual_count > 0 and voice_count > 0:
        return "active"
    return "active_partial"


def _reason(status: str) -> str:
    return {
        "waiting_for_stage10": "stage10_life_loop_not_ready",
        "active_waiting_for_sensory_events": "no_visual_or_voice_events_observed_yet",
        "needs_check": "sensory_event_contract_missing_required_fields",
        "active": "visual_and_voice_events_connected_to_perception",
        "active_partial": "one_sensory_source_connected_other_waiting_for_live_event",
    }.get(status, "unknown")


def _sensory_route_status(
    *,
    visual_count: int,
    voice_count: int,
    importance: dict[str, Any],
) -> str:
    metrics = importance.get("metrics") if isinstance(importance.get("metrics"), dict) else {}
    sensory_judgments = _int_value(metrics.get("sensory_observation_count"))
    owner_attention = _int_value(metrics.get("owner_attention_count"))
    if visual_count > 0 and voice_count > 0 and sensory_judgments > 0 and owner_attention > 0:
        return "visual_and_voice_can_influence_internal_gaps"
    if visual_count > 0 and sensory_judgments > 0:
        return "visual_can_influence_internal_gaps_voice_waiting"
    if voice_count > 0 and owner_attention > 0:
        return "voice_can_influence_owner_attention_visual_waiting"
    return "waiting_for_multisensory_importance_judgment"


def build_stage11_multisensory_extension(root: Path | str, *, generated_at: str | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    generated_at = generated_at or _now_iso()
    stage10 = build_stage10_proactive_life_loop(root, generated_at=generated_at)
    stage10_ready = bool(stage10.get("ready_for_stage11"))
    visual_ingress = build_stage11_visual_ingress_diagnostics(root, generated_at=generated_at)
    visual_ingress_model = visual_ingress.get("model") if isinstance(visual_ingress.get("model"), dict) else {}
    voice_ingress = build_stage11_voice_ingress_diagnostics(root, generated_at=generated_at)
    voice_ingress_model = voice_ingress.get("model") if isinstance(voice_ingress.get("model"), dict) else {}
    event_layer = build_perception_event_layer_report(root, generated_at=generated_at)
    importance = build_perception_importance_report(root, generated_at=generated_at, perception_event_layer=event_layer)
    event_metrics = event_layer.get("metrics") if isinstance(event_layer.get("metrics"), dict) else {}
    importance_metrics = importance.get("metrics") if isinstance(importance.get("metrics"), dict) else {}
    visual_count = _int_value(event_metrics.get("visual_event_count"))
    voice_count = _int_value(event_metrics.get("voice_event_count"))
    sensory_events = _sensory_events(event_layer)
    contract = _sensory_event_contract(sensory_events)
    signal = perception_gap_signal(importance)
    route_status = _sensory_route_status(visual_count=visual_count, voice_count=voice_count, importance=importance)
    status = _status(
        stage10_ready=stage10_ready,
        visual_count=visual_count,
        voice_count=voice_count,
        contract_ok=bool(contract.get("sensory_event_contract_ok")),
    )
    boundaries = {
        "raw_owner_text_in_state": False,
        "raw_visual_body_in_state": False,
        "raw_voice_transcript_in_state": False,
        "raw_image_bytes_retained": False,
        "raw_audio_bytes_retained": False,
        "model_inference_written_as_fact": False,
        "stable_memory_write": "blocked",
        "qq_message_enqueued": False,
        "consciousness_claim": False,
    }
    gate_proof = {
        "visual_or_voice_events_have_source_time_confidence_privacy_ref": bool(
            contract.get("sensory_event_contract_ok")
        ),
        "model_inference_kept_as_observation_not_fact": True,
        "sensory_events_enter_importance_judgment": (
            _int_value(importance_metrics.get("sensory_observation_count")) > 0
            or (voice_count > 0 and _int_value(importance_metrics.get("owner_attention_count")) > 0)
        ),
        "sensory_results_can_change_candidate_route": route_status
        in {
            "visual_and_voice_can_influence_internal_gaps",
            "visual_can_influence_internal_gaps_voice_waiting",
            "voice_can_influence_owner_attention_visual_waiting",
        },
    }
    ready_for_stage12 = status == "active" and all(bool(value) for value in gate_proof.values())
    model = {
        "stage10_ready_for_stage11": stage10_ready,
        "visual_event_count": visual_count,
        "voice_event_count": voice_count,
        "multimodal_event_count": visual_count + voice_count,
        "sensory_event_count": contract.get("sensory_event_count", 0),
        "sensory_required_field_missing_count": contract.get("sensory_required_field_missing_count", 0),
        "sensory_confidence_ready_count": contract.get("sensory_confidence_ready_count", 0),
        "sensory_privacy_ready_count": contract.get("sensory_privacy_ready_count", 0),
        "sensory_observation_judgment_count": _int_value(importance_metrics.get("sensory_observation_count")),
        "owner_attention_judgment_count": _int_value(importance_metrics.get("owner_attention_count")),
        "priority_gap_type": _one_line(signal.get("gap_type"), limit=120),
        "priority_route_hint": _one_line(signal.get("route_hint"), limit=180),
        "priority_future_effect": _one_line(signal.get("future_effect"), limit=220),
        "sensory_route_status": route_status,
        "visual_ingress_status": _one_line(visual_ingress.get("status"), limit=120),
        "visual_ingress_payload_row_count": _int_value(visual_ingress_model.get("visual_payload_row_count")),
        "visual_ingress_image_context_available_count": _int_value(
            visual_ingress_model.get("image_context_available_count")
        ),
        "visual_ingress_image_context_vision_result_count": _int_value(
            visual_ingress_model.get("image_context_vision_result_count")
        ),
        "visual_ingress_ocr_result_count": _int_value(visual_ingress_model.get("ocr_result_count")),
        "visual_ingress_evidence_mode": _one_line(visual_ingress_model.get("evidence_mode"), limit=120),
        "visual_ingress_next_step": _one_line(visual_ingress_model.get("next_step"), limit=180),
        "voice_ingress_status": _one_line(voice_ingress.get("status"), limit=120),
        "voice_ingress_payload_row_count": _int_value(voice_ingress_model.get("voice_payload_row_count")),
        "voice_ingress_transcript_result_count": _int_value(voice_ingress_model.get("voice_transcript_result_count")),
        "voice_ingress_evidence_mode": _one_line(voice_ingress_model.get("evidence_mode"), limit=120),
        "voice_ingress_next_step": _one_line(voice_ingress_model.get("next_step"), limit=180),
        "fact_boundary": "observation_not_fact",
        "next_step": _next_step(status, visual_count=visual_count, voice_count=voice_count),
        "stage11_contract": "multisensory_events_as_bounded_perception_inputs_not_claimed_reality",
    }
    return {
        "ok": True,
        "generated_at": generated_at,
        "root": str(root),
        "stage": "stage11_multisensory_extension",
        "status": status,
        "ready_for_stage12": ready_for_stage12,
        "reason": _reason(status),
        "model": model,
        "gate_proof": gate_proof,
        "evidence_refs": {
            "stage10_proactive_life_loop": "memory/context/stage10_proactive_life_loop_state.md",
            "perception_event_layer": "memory/context/perception_event_layer_state.md",
            "perception_importance": "memory/context/perception_importance_state.md",
            "ocr_trace": "runtime/learning_ocr_trace.jsonl",
            "voice_trace": "runtime/voice_input_trace.jsonl",
            "visual_ingress_diagnostics": "memory/context/stage11_visual_ingress_diagnostics_state.md",
            "voice_ingress_diagnostics": "memory/context/stage11_voice_ingress_diagnostics_state.md",
        },
        "sensory_event_refs": _sensory_event_refs(sensory_events),
        "boundaries": boundaries,
    }


def _next_step(status: str, *, visual_count: int, voice_count: int) -> str:
    if status == "waiting_for_stage10":
        return "finish_stage10_proactive_life_loop_first"
    if visual_count <= 0 and voice_count <= 0:
        return "wait_for_or_inject_visual_or_voice_event_trace"
    if visual_count > 0 and voice_count <= 0:
        return "connect_or_capture_voice_transcript_event"
    if voice_count > 0 and visual_count <= 0:
        return "connect_or_capture_visual_ocr_event"
    if status == "needs_check":
        return "repair_sensory_event_required_fields"
    return "stage12_long_term_evaluation_can_start"


def _sensory_event_refs(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for event in events[:8]:
        refs.append(
            {
                "event_id": _one_line(event.get("event_id"), limit=100),
                "event_type": _one_line(event.get("event_type"), limit=100),
                "source": _one_line(event.get("source"), limit=100),
                "confidence": _one_line(event.get("confidence"), limit=80),
                "privacy_scope": _one_line(event.get("privacy_scope"), limit=100),
                "evidence_ref": _one_line(event.get("evidence_ref"), limit=160),
            }
        )
    return refs


def render_stage11_multisensory_extension(report: dict[str, Any]) -> str:
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    gate_proof = report.get("gate_proof") if isinstance(report.get("gate_proof"), dict) else {}
    boundaries = report.get("boundaries") if isinstance(report.get("boundaries"), dict) else {}
    sensory_refs = report.get("sensory_event_refs") if isinstance(report.get("sensory_event_refs"), list) else []
    lines = [
        "# XinYu Stage 11 Multisensory Extension",
        "",
        f"- generated_at: {_one_line(report.get('generated_at'))}",
        f"- status: {_one_line(report.get('status'))}",
        f"- ready_for_stage12: {_bool_text(report.get('ready_for_stage12', False))}",
        f"- reason: {_one_line(report.get('reason'))}",
        "- claim_boundary: multisensory perception inputs only; no consciousness claim",
        "",
        "## Multisensory State",
    ]
    for key in (
        "stage10_ready_for_stage11",
        "visual_event_count",
        "voice_event_count",
        "multimodal_event_count",
        "sensory_event_count",
        "sensory_required_field_missing_count",
        "sensory_confidence_ready_count",
        "sensory_privacy_ready_count",
        "sensory_observation_judgment_count",
        "owner_attention_judgment_count",
        "priority_gap_type",
        "priority_route_hint",
        "priority_future_effect",
        "sensory_route_status",
        "visual_ingress_status",
        "visual_ingress_payload_row_count",
        "visual_ingress_image_context_available_count",
        "visual_ingress_image_context_vision_result_count",
        "visual_ingress_ocr_result_count",
        "visual_ingress_evidence_mode",
        "visual_ingress_next_step",
        "voice_ingress_status",
        "voice_ingress_payload_row_count",
        "voice_ingress_transcript_result_count",
        "voice_ingress_evidence_mode",
        "voice_ingress_next_step",
        "fact_boundary",
        "next_step",
        "stage11_contract",
    ):
        value = model.get(key, "missing")
        lines.append(f"- {key}: {_bool_text(value) if isinstance(value, bool) else _one_line(value, limit=240)}")
    lines.extend(["", "## Sensory Event Refs"])
    if sensory_refs:
        for item in sensory_refs:
            lines.append(
                "- "
                f"{_one_line(item.get('event_type'), limit=100)} "
                f"source={_one_line(item.get('source'), limit=100)} "
                f"confidence={_one_line(item.get('confidence'), limit=80)} "
                f"privacy={_one_line(item.get('privacy_scope'), limit=100)} "
                f"ref={_one_line(item.get('evidence_ref'), limit=120)}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Gate Proof"])
    for key in sorted(gate_proof):
        lines.append(f"- {key}: {_bool_text(gate_proof.get(key))}")
    lines.extend(["", "## Evidence Refs"])
    evidence = report.get("evidence_refs") if isinstance(report.get("evidence_refs"), dict) else {}
    for key in sorted(evidence):
        lines.append(f"- {key}: {_one_line(evidence.get(key), limit=180)}")
    lines.extend(["", "## Boundaries"])
    for key in sorted(boundaries):
        value = boundaries.get(key)
        lines.append(f"- {key}: {_bool_text(value) if isinstance(value, bool) else _one_line(value)}")
    return "\n".join(lines).rstrip() + "\n"


def write_stage11_multisensory_extension_report(
    root: Path | str,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> Path:
    return write_stage11_multisensory_report_text(
        root,
        render_stage11_multisensory_extension(report),
        output=output,
    )


def write_stage11_multisensory_extension_state(
    root: Path | str,
    report: dict[str, Any],
    *,
    report_path: Path | None = None,
) -> Path:
    root = Path(root).resolve()
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    gate_proof = report.get("gate_proof") if isinstance(report.get("gate_proof"), dict) else {}
    boundaries = report.get("boundaries") if isinstance(report.get("boundaries"), dict) else {}
    target_report = report_path or stage11_multisensory_report_path(root)
    text = f"""---
title: Stage 11 Multisensory Extension State
memory_type: stage11_multisensory_extension_state
time_scope: immediate_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_stage11_multisensory_extension
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, multisensory, perception, stage11, audit]
---

# Stage 11 Multisensory Extension State

## Gate
- stage11_multisensory_extension_status: {report.get('status', 'missing')}
- stage11_ready_for_stage12: {_bool_text(report.get('ready_for_stage12', False))}
- stage11_reason: {report.get('reason', 'missing')}

## Current Multisensory State
- stage11_stage10_ready_for_stage11: {_bool_text(model.get('stage10_ready_for_stage11', False))}
- stage11_visual_event_count: {model.get('visual_event_count', '0')}
- stage11_voice_event_count: {model.get('voice_event_count', '0')}
- stage11_multimodal_event_count: {model.get('multimodal_event_count', '0')}
- stage11_sensory_event_count: {model.get('sensory_event_count', '0')}
- stage11_sensory_required_field_missing_count: {model.get('sensory_required_field_missing_count', '0')}
- stage11_sensory_confidence_ready_count: {model.get('sensory_confidence_ready_count', '0')}
- stage11_sensory_privacy_ready_count: {model.get('sensory_privacy_ready_count', '0')}
- stage11_sensory_observation_judgment_count: {model.get('sensory_observation_judgment_count', '0')}
- stage11_owner_attention_judgment_count: {model.get('owner_attention_judgment_count', '0')}
- stage11_priority_gap_type: {model.get('priority_gap_type', 'none')}
- stage11_priority_route_hint: {model.get('priority_route_hint', 'none')}
- stage11_priority_future_effect: {model.get('priority_future_effect', 'none')}
- stage11_sensory_route_status: {model.get('sensory_route_status', 'none')}
- stage11_visual_ingress_status: {model.get('visual_ingress_status', 'none')}
- stage11_visual_ingress_payload_row_count: {model.get('visual_ingress_payload_row_count', '0')}
- stage11_visual_ingress_image_context_available_count: {model.get('visual_ingress_image_context_available_count', '0')}
- stage11_visual_ingress_image_context_vision_result_count: {model.get('visual_ingress_image_context_vision_result_count', '0')}
- stage11_visual_ingress_ocr_result_count: {model.get('visual_ingress_ocr_result_count', '0')}
- stage11_visual_ingress_evidence_mode: {model.get('visual_ingress_evidence_mode', 'none')}
- stage11_visual_ingress_next_step: {model.get('visual_ingress_next_step', 'none')}
- stage11_voice_ingress_status: {model.get('voice_ingress_status', 'none')}
- stage11_voice_ingress_payload_row_count: {model.get('voice_ingress_payload_row_count', '0')}
- stage11_voice_ingress_transcript_result_count: {model.get('voice_ingress_transcript_result_count', '0')}
- stage11_voice_ingress_evidence_mode: {model.get('voice_ingress_evidence_mode', 'none')}
- stage11_voice_ingress_next_step: {model.get('voice_ingress_next_step', 'none')}
- stage11_fact_boundary: {model.get('fact_boundary', 'missing')}
- stage11_next_step: {model.get('next_step', 'missing')}
- stage11_contract: {model.get('stage11_contract', 'missing')}

## Gate Proof
- visual_or_voice_events_have_source_time_confidence_privacy_ref: {_bool_text(gate_proof.get('visual_or_voice_events_have_source_time_confidence_privacy_ref'))}
- model_inference_kept_as_observation_not_fact: {_bool_text(gate_proof.get('model_inference_kept_as_observation_not_fact'))}
- sensory_events_enter_importance_judgment: {_bool_text(gate_proof.get('sensory_events_enter_importance_judgment'))}
- sensory_results_can_change_candidate_route: {_bool_text(gate_proof.get('sensory_results_can_change_candidate_route'))}

## Boundaries
- raw_owner_text_in_state: {_bool_text(boundaries.get('raw_owner_text_in_state', False))}
- raw_visual_body_in_state: {_bool_text(boundaries.get('raw_visual_body_in_state', False))}
- raw_voice_transcript_in_state: {_bool_text(boundaries.get('raw_voice_transcript_in_state', False))}
- raw_image_bytes_retained: {_bool_text(boundaries.get('raw_image_bytes_retained', False))}
- raw_audio_bytes_retained: {_bool_text(boundaries.get('raw_audio_bytes_retained', False))}
- model_inference_written_as_fact: {_bool_text(boundaries.get('model_inference_written_as_fact', False))}
- stable_memory_write: {boundaries.get('stable_memory_write', 'blocked')}
- qq_message_enqueued: {_bool_text(boundaries.get('qq_message_enqueued', False))}
- consciousness_claim: {_bool_text(boundaries.get('consciousness_claim', False))}
- report_path: {target_report.as_posix()}
"""
    return write_stage11_multisensory_state_text(root, text)


def append_stage11_multisensory_extension_trace(root: Path | str, report: dict[str, Any]) -> Path:
    root = Path(root).resolve()
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    event = {
        "event_id": "stage11-multisensory-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S"),
        "observed_at": report.get("generated_at", _now_iso()),
        "status": report.get("status", "missing"),
        "ready_for_stage12": bool(report.get("ready_for_stage12", False)),
        "visual_event_count": model.get("visual_event_count", "0"),
        "voice_event_count": model.get("voice_event_count", "0"),
        "sensory_event_count": model.get("sensory_event_count", "0"),
        "sensory_route_status": model.get("sensory_route_status", "none"),
        "visual_ingress_status": model.get("visual_ingress_status", "none"),
        "visual_ingress_payload_row_count": model.get("visual_ingress_payload_row_count", "0"),
        "visual_ingress_image_context_available_count": model.get(
            "visual_ingress_image_context_available_count",
            "0",
        ),
        "visual_ingress_image_context_vision_result_count": model.get(
            "visual_ingress_image_context_vision_result_count",
            "0",
        ),
        "visual_ingress_ocr_result_count": model.get("visual_ingress_ocr_result_count", "0"),
        "voice_ingress_status": model.get("voice_ingress_status", "none"),
        "voice_ingress_payload_row_count": model.get("voice_ingress_payload_row_count", "0"),
        "voice_ingress_transcript_result_count": model.get("voice_ingress_transcript_result_count", "0"),
        "fact_boundary": model.get("fact_boundary", "missing"),
        "raw_owner_text_retained": False,
        "raw_visual_body_retained": False,
        "raw_voice_transcript_retained": False,
        "qq_message_enqueued": False,
        "consciousness_claim": False,
    }
    return append_stage11_multisensory_trace_event(root, event)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build XinYu Stage 11 multisensory extension report.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    report = build_stage11_multisensory_extension(args.root)
    if args.write:
        report_path = write_stage11_multisensory_extension_report(args.root, report, output=args.output)
        state_path = write_stage11_multisensory_extension_state(args.root, report, report_path=report_path)
        trace_path = append_stage11_multisensory_extension_trace(args.root, report)
        report["report_path"] = str(report_path)
        report["state_path"] = str(state_path)
        report["trace_path"] = str(trace_path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_stage11_multisensory_extension(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
