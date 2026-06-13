from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_action_feedback_coverage import build_action_feedback_coverage_report
from xinyu_perception_event_layer_store import OCR_TRACE_REL
from xinyu_perception_event_layer_store import PROACTIVE_REQUEST_STATE_REL
from xinyu_perception_event_layer_store import QQ_ACK_REL
from xinyu_perception_event_layer_store import QQ_TRACE_REL
from xinyu_perception_event_layer_store import REPORT_REL
from xinyu_perception_event_layer_store import STATE_REL
from xinyu_perception_event_layer_store import TRACE_REL
from xinyu_perception_event_layer_store import VOICE_TRACE_RELS
from xinyu_perception_event_layer_store import append_perception_event_layer_trace_event
from xinyu_perception_event_layer_store import perception_event_layer_state_path
from xinyu_perception_event_layer_store import read_perception_event_layer_jsonl_tail
from xinyu_perception_event_layer_store import read_perception_event_layer_proactive_request_state_text
from xinyu_perception_event_layer_store import read_perception_event_layer_state_text
from xinyu_perception_event_layer_store import write_perception_event_layer_report_text
from xinyu_perception_event_layer_store import write_perception_event_layer_state_text

NONE_VALUES = {"", "missing", "none", "unknown", "null"}
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bpassword\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)


def build_perception_event_layer_report(
    root: Path,
    *,
    generated_at: str | None = None,
    action_feedback_coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    generated_at = generated_at or _now_iso()
    events: list[dict[str, Any]] = []
    events.extend(_qq_events(root, generated_at=generated_at))
    events.extend(_desktop_events(root, generated_at=generated_at))
    events.extend(_multimodal_events(root, generated_at=generated_at))
    coverage = (
        action_feedback_coverage
        if isinstance(action_feedback_coverage, dict)
        else build_action_feedback_coverage_report(root, generated_at=generated_at)
    )
    events.extend(_action_surface_events(coverage, generated_at=generated_at))
    events = _dedupe_events(events)
    metrics = _metrics(events)
    status = _status(metrics)

    return {
        "ok": status in {"pass", "partial"},
        "status": status,
        "generated_at": generated_at,
        "root": str(root),
        "metrics": metrics,
        "events": [_public_event(event) for event in events[:16]],
        "privacy": {
            "raw_private_body_retained": False,
            "visible_reply_text_retained": False,
            "private_text_in_report": False,
            "stable_memory_write": "blocked",
        },
        "notes": _notes(status, metrics),
    }


def render_perception_event_layer_report(report: dict[str, Any]) -> str:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    events = report.get("events") if isinstance(report.get("events"), list) else []
    lines = [
        "# XinYu Perception Event Layer",
        "",
        f"- generated_at: {report.get('generated_at', 'unknown')}",
        f"- status: {report.get('status', 'unknown')}",
        f"- result: {'pass' if report.get('ok') else 'needs_check'}",
        "- claim_boundary: normalized input/event evidence only; does not claim consciousness",
        "",
        "## Metrics",
    ]
    for key in (
        "event_count",
        "source_count",
        "event_type_count",
        "input_event_count",
        "qq_event_count",
        "desktop_event_count",
        "tool_result_event_count",
        "system_health_event_count",
        "file_change_event_count",
        "visual_event_count",
        "voice_event_count",
        "multimodal_event_count",
        "sensory_event_count",
        "importance_ready_count",
        "anomaly_count",
        "privacy_scope_count",
        "latest_event_type",
        "latest_event_source",
        "latest_event_ref",
    ):
        lines.append(f"- {key}: {metrics.get(key, 'missing')}")
    lines.extend(["", "## Recent Events"])
    if events:
        for event in events[:16]:
            lines.append(f"### {event.get('event_id', 'unknown')}")
            for key in (
                "event_type",
                "source",
                "observed_at",
                "confidence",
                "privacy_scope",
                "importance",
                "anomaly",
                "summary",
                "evidence_ref",
            ):
                lines.append(f"- {key}: {event.get(key, 'missing')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Privacy Boundary"])
    for key, value in privacy.items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Notes"])
    notes = report.get("notes") if isinstance(report.get("notes"), list) else []
    lines.extend(f"- {note}" for note in notes) if notes else lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def write_perception_event_layer_report(
    root: Path,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> dict[str, str]:
    root = Path(root).resolve()
    report_path = write_perception_event_layer_report_text(
        root,
        render_perception_event_layer_report(report),
        output=output,
    )
    _write_state(root, report, report_path=report_path)
    _append_trace(root, report)
    return {"report_path": str(report_path), "state_path": str(perception_event_layer_state_path(root))}


def read_perception_event_layer_state(root: Path) -> dict[str, str]:
    text = read_perception_event_layer_state_text(root)
    if not text:
        return {"status": "missing", "event_count": "0", "source_count": "0"}
    return _parse_fields(text)


def _qq_events(root: Path, *, generated_at: str) -> list[dict[str, Any]]:
    rows = _read_jsonl_tail(root / QQ_TRACE_REL, max_lines=800)
    events: list[dict[str, Any]] = []
    latest_private = _latest(
        rows,
        lambda row: row.get("message_kind") == "private"
        and row.get("stage") in {"queued", "prepared", "coalesced_wait"},
    )
    if latest_private:
        events.append(
            _event(
                "owner_text_input",
                "qq",
                _row_time_text(latest_private) or generated_at,
                confidence="high",
                privacy_scope="owner_private",
                evidence_ref=_ref(latest_private.get("message_id") or latest_private.get("arrival_seq")),
                summary=(
                    f"owner private input observed stage={_one_line(latest_private.get('stage'))} "
                    f"text_len={_one_line(latest_private.get('text_len'))}"
                ),
                importance="high",
                anomaly=False,
            )
        )
    latest_stale_drop = _latest(rows, lambda row: row.get("stage") == "stale_reply_dropped")
    if latest_stale_drop:
        events.append(
            _event(
                "qq_drop",
                "qq_gateway",
                _row_time_text(latest_stale_drop) or generated_at,
                confidence="high",
                privacy_scope="owner_private",
                evidence_ref=_ref(latest_stale_drop.get("message_id") or latest_stale_drop.get("arrival_seq")),
                summary=f"stale visible reply dropped reason={_one_line(latest_stale_drop.get('drop_reason'))}",
                importance="high",
                anomaly=True,
            )
        )
    latest_group_drop = _latest(
        rows,
        lambda row: row.get("message_kind") == "group" and row.get("stage") == "dropped",
    )
    if latest_group_drop:
        events.append(
            _event(
                "qq_group_boundary",
                "qq_gateway",
                _row_time_text(latest_group_drop) or generated_at,
                confidence="high",
                privacy_scope="group",
                evidence_ref=_ref(latest_group_drop.get("message_id") or latest_group_drop.get("arrival_seq")),
                summary=f"group event bounded reason={_one_line(latest_group_drop.get('drop_reason') or 'dropped')}",
                importance="boundary",
                anomaly=False,
            )
        )
    ack = _latest(_ack_records(root / QQ_ACK_REL), lambda row: row.get("event_type") == "ack")
    if ack:
        events.append(
            _event(
                "qq_ack",
                "qq_gateway",
                _one_line(ack.get("observed_at")) or generated_at,
                confidence="high",
                privacy_scope="owner_private" if ack.get("message_type") != "group" else "group",
                evidence_ref=_ref(ack.get("key") or ack.get("adapter_message_id") or ack.get("source_message_id")),
                summary=f"QQ ack observed route={_one_line(ack.get('route'))}",
                importance="normal",
                anomaly=False,
            )
        )
    return events


def _desktop_events(root: Path, *, generated_at: str) -> list[dict[str, Any]]:
    fields = _parse_fields(read_perception_event_layer_proactive_request_state_text(root))
    status = fields.get("status", "missing")
    answer_state = fields.get("request_answer_state", "missing")
    last_ack = fields.get("last_ack_status", "missing")
    adapter_error = fields.get("adapter_error", "missing")
    if not any(_present(value) for value in (status, answer_state, last_ack, adapter_error)):
        return []
    anomaly = _present(adapter_error)
    importance = "high" if anomaly or answer_state in {"reply", "replied", "answered", "owner_replied", "approved_qq"} else "normal"
    return [
        _event(
            "desktop_ack",
            "desktop",
            _none_to_empty(fields.get("checked_at"))
            or _none_to_empty(fields.get("updated_at"))
            or _none_to_empty(fields.get("created_at"))
            or generated_at,
            confidence="medium",
            privacy_scope="owner_private",
            evidence_ref=_ref(fields.get("request_id") or fields.get("thread_id") or fields.get("last_claim_id")),
            summary=(
                f"desktop request state status={_one_line(status)} "
                f"answer={_one_line(answer_state)} ack={_one_line(last_ack)}"
            ),
            importance=importance,
            anomaly=anomaly,
        )
    ]


def _action_surface_events(report: dict[str, Any], *, generated_at: str) -> list[dict[str, Any]]:
    surfaces = report.get("surfaces") if isinstance(report.get("surfaces"), dict) else {}
    events: list[dict[str, Any]] = []
    for name, surface in surfaces.items():
        if not isinstance(surface, dict) or not surface.get("observed"):
            continue
        event_type = _surface_event_type(str(name), surface)
        anomaly = surface.get("surface_status") == "needs_check" or _result_failed(surface.get("action_result"))
        privacy_scope = "owner_private" if name in {"qq", "desktop"} else "runtime"
        events.append(
            _event(
                event_type,
                str(name),
                _none_to_empty(surface.get("checked_at")) or generated_at,
                confidence="medium",
                privacy_scope=privacy_scope,
                evidence_ref=_none_to_empty(surface.get("evidence_ref")) or _ref(name),
                summary=(
                    f"{_one_line(name)} feedback={_one_line(surface.get('feedback_signal'))} "
                    f"result={_one_line(surface.get('action_result'))} "
                    f"status={_one_line(surface.get('surface_status'))}"
                ),
                importance="high" if anomaly else "normal",
                anomaly=anomaly,
            )
        )
    return events


def _multimodal_events(root: Path, *, generated_at: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    events.extend(_qq_visual_events(root, generated_at=generated_at))
    events.extend(_ocr_events(root, generated_at=generated_at))
    events.extend(_voice_events(root, generated_at=generated_at))
    return events


def _qq_visual_events(root: Path, *, generated_at: str) -> list[dict[str, Any]]:
    rows = _read_jsonl_tail(root / QQ_TRACE_REL, max_lines=800)
    latest = _latest(
        rows,
        lambda row: _int(row.get("image_count")) > 0 or _int(row.get("sticker_count")) > 0,
    )
    if not latest:
        return []
    image_count = _int(latest.get("image_count"))
    sticker_count = _int(latest.get("sticker_count"))
    drop_reason = _one_line(latest.get("drop_reason"))
    confidence = "medium" if image_count > 0 else "low"
    if drop_reason in {"", "none", "missing"} and image_count > 0:
        confidence = "medium"
    privacy_scope = "owner_private" if latest.get("message_kind") == "private" else "group"
    return [
        _event(
            "visual_observation_result",
            "qq_visual",
            _row_time_text(latest) or generated_at,
            confidence=confidence,
            privacy_scope=privacy_scope,
            evidence_ref=_ref(latest.get("message_id") or latest.get("arrival_seq")),
            summary=(
                "qq rich visual payload observed "
                f"image_count={image_count} sticker_count={sticker_count} "
                f"content_interpreted=false drop_reason={drop_reason or 'none'}"
            ),
            importance="boundary" if privacy_scope == "group" else "normal",
            anomaly=False,
        )
    ]


def _ocr_events(root: Path, *, generated_at: str) -> list[dict[str, Any]]:
    latest = _latest(_read_jsonl_tail(root / OCR_TRACE_REL, max_lines=200), lambda row: True)
    if not latest:
        return []
    stdout = _one_line(latest.get("stdout"), limit=2000)
    status = _one_line(latest.get("status")) or ("ok" if stdout else "unknown")
    returncode = _one_line(latest.get("returncode"))
    text_len = len(stdout)
    failed = returncode not in {"", "0", "none"} or "error" in status.lower() or "failed" in status.lower()
    confidence = "high" if text_len > 0 and not failed else "low" if text_len <= 0 else "medium"
    return [
        _event(
            "visual_observation_result",
            "ocr",
            _row_time_text(latest) or generated_at,
            confidence=confidence,
            privacy_scope="owner_private",
            evidence_ref=_ref(latest.get("path") or f"ocr:{status}:{returncode}:{text_len}"),
            summary=(
                f"ocr observation result status={status or 'unknown'} returncode={returncode or 'unknown'} "
                f"text_len={text_len} raw_text_retained=false"
            ),
            importance="high" if text_len > 0 else "normal",
            anomaly=failed,
        )
    ]


def _voice_events(root: Path, *, generated_at: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    latest_trace = _latest(_voice_trace_rows(root), lambda row: True)
    if latest_trace:
        transcript = _one_line(
            latest_trace.get("transcript")
            or latest_trace.get("transcript_text")
            or latest_trace.get("text")
            or latest_trace.get("stdout"),
            limit=2000,
        )
        status = _one_line(latest_trace.get("status") or latest_trace.get("event_kind")) or "observed"
        confidence = _confidence_from_value(latest_trace.get("confidence"), default="high" if transcript else "low")
        failed = any(marker in status.lower() for marker in ("fail", "error", "timeout"))
        events.append(
            _event(
                "voice_input_result",
                "voice_transcript",
                _row_time_text(latest_trace) or generated_at,
                confidence=confidence,
                privacy_scope="owner_private",
                evidence_ref=_ref(latest_trace.get("event_id") or latest_trace.get("message_id") or status),
                summary=(
                    f"voice transcript result status={status} transcript_len={len(transcript)} "
                    "raw_transcript_retained=false"
                ),
                importance="high" if transcript else "normal",
                anomaly=failed,
            )
        )
    latest_qq_voice = _latest(
        _read_jsonl_tail(root / QQ_TRACE_REL, max_lines=800),
        lambda row: _qq_row_has_voice_payload(row),
    )
    if latest_qq_voice:
        events.append(
            _event(
                "voice_input_result",
                "qq_voice",
                _row_time_text(latest_qq_voice) or generated_at,
                confidence="low",
                privacy_scope="owner_private" if latest_qq_voice.get("message_kind") == "private" else "group",
                evidence_ref=_ref(latest_qq_voice.get("message_id") or latest_qq_voice.get("arrival_seq")),
                summary="qq voice/audio payload observed transcript_available=false raw_audio_retained=false",
                importance="normal",
                anomaly=False,
            )
        )
    return events


def _voice_trace_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in VOICE_TRACE_RELS:
        rows.extend(_read_jsonl_tail(root / rel, max_lines=200))
    return rows


def _qq_row_has_voice_payload(row: dict[str, Any]) -> bool:
    if (
        _int(row.get("voice_count")) > 0
        or _int(row.get("audio_count")) > 0
        or _int(row.get("record_count")) > 0
        or _int(row.get("qq_voice_count")) > 0
        or _int(row.get("qq_audio_count")) > 0
        or _int(row.get("qq_record_count")) > 0
    ):
        return True
    summary = _one_line(row.get("rich_summary")).lower()
    if any(marker in summary for marker in ("\u8bed\u97f3", "\u97f3\u9891")):
        return True
    return any(marker in summary for marker in ("语音", "音频", "voice", "audio", "record"))


def _confidence_from_value(value: Any, *, default: str) -> str:
    text = _one_line(value).lower()
    if text in {"low", "medium", "high"}:
        return text
    try:
        number = float(text)
    except ValueError:
        return default
    if number >= 0.8:
        return "high"
    if number >= 0.45:
        return "medium"
    return "low"


def _surface_event_type(name: str, surface: dict[str, Any]) -> str:
    signal = _one_line(surface.get("feedback_signal"))
    if name == "code_probe" and ("source_changed" in signal or "restart_required" in signal):
        return "file_change"
    if name in {"runtime_probe", "code_probe"}:
        return "system_health_change"
    if name == "desktop":
        return "desktop_ack"
    if name == "qq":
        return "qq_ack" if "ack" in signal else "qq_drop" if "drop" in signal else "qq_feedback"
    return "tool_execution_result"


def _event(
    event_type: str,
    source: str,
    observed_at: str,
    *,
    confidence: str,
    privacy_scope: str,
    evidence_ref: str,
    summary: str,
    importance: str,
    anomaly: bool,
) -> dict[str, Any]:
    source = _clean_token(source, default="unknown")
    event_type = _clean_token(event_type, default="unknown")
    observed_at = _none_to_empty(observed_at) or "unknown"
    evidence_ref = _none_to_empty(evidence_ref) or _ref(f"{source}:{event_type}:{observed_at}")
    summary = _one_line(summary, limit=180) or "event observed"
    event_id = "percevt-" + _hash(f"{source}|{event_type}|{observed_at}|{evidence_ref}")[:16]
    return {
        "event_id": event_id,
        "event_type": event_type,
        "source": source,
        "observed_at": observed_at,
        "confidence": confidence if confidence in {"low", "medium", "high"} else "medium",
        "privacy_scope": _clean_token(privacy_scope, default="runtime"),
        "evidence_ref": evidence_ref,
        "summary": summary,
        "importance": importance if importance in {"low", "normal", "high", "boundary"} else "normal",
        "anomaly": bool(anomaly),
        "raw_private_body_retained": False,
        "visible_text_retained": False,
    }


def _metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    sources = {str(event.get("source", "")) for event in events if _present(event.get("source"))}
    event_types = {str(event.get("event_type", "")) for event in events if _present(event.get("event_type"))}
    latest = _latest_event(events)
    visual_event_count = _count(events, "visual_observation_result")
    voice_event_count = _count(events, "voice_input_result")
    return {
        "event_count": len(events),
        "source_count": len(sources),
        "event_type_count": len(event_types),
        "input_event_count": _count(events, "owner_text_input"),
        "qq_event_count": sum(1 for event in events if str(event.get("event_type", "")).startswith("qq_")),
        "desktop_event_count": _count(events, "desktop_ack"),
        "tool_result_event_count": _count(events, "tool_execution_result"),
        "system_health_event_count": _count(events, "system_health_change"),
        "file_change_event_count": _count(events, "file_change"),
        "visual_event_count": visual_event_count,
        "voice_event_count": voice_event_count,
        "multimodal_event_count": visual_event_count + voice_event_count,
        "sensory_event_count": visual_event_count + voice_event_count,
        "importance_ready_count": sum(1 for event in events if _present(event.get("importance"))),
        "anomaly_count": sum(1 for event in events if event.get("anomaly") is True),
        "privacy_scope_count": len({str(event.get("privacy_scope", "")) for event in events if _present(event.get("privacy_scope"))}),
        "latest_event_type": latest.get("event_type", "none"),
        "latest_event_source": latest.get("source", "none"),
        "latest_event_ref": latest.get("evidence_ref", "none"),
    }


def _status(metrics: dict[str, Any]) -> str:
    event_count = _int(metrics.get("event_count"))
    input_count = _int(metrics.get("input_event_count"))
    source_count = _int(metrics.get("source_count"))
    importance_count = _int(metrics.get("importance_ready_count"))
    if event_count <= 0:
        return "no_events"
    if importance_count < event_count:
        return "needs_check"
    if input_count >= 1 and source_count >= 2:
        return "pass"
    return "partial"


def _notes(status: str, metrics: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    if status == "no_events":
        notes.append("no_perception_events_observed")
    if _int(metrics.get("input_event_count")) <= 0:
        notes.append("owner_text_input_not_observed_in_event_layer")
    if _int(metrics.get("tool_result_event_count")) > 0:
        notes.append("tool_result_events_unified")
    if _int(metrics.get("system_health_event_count")) > 0:
        notes.append("system_health_events_unified")
    if _int(metrics.get("file_change_event_count")) > 0:
        notes.append("file_change_events_unified")
    if _int(metrics.get("visual_event_count")) <= 0:
        notes.append("visual_events_not_connected_yet")
    if _int(metrics.get("voice_event_count")) <= 0:
        notes.append("voice_events_not_connected_yet")
    if _int(metrics.get("anomaly_count")) > 0:
        notes.append("anomaly_events_ready_for_importance_judgement")
    if status == "pass":
        notes.append("perception_events_have_source_time_privacy_confidence_and_refs")
    return notes


def _write_state(root: Path, report: dict[str, Any], *, report_path: Path) -> None:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    text = f"""---
title: Perception Event Layer State
memory_type: perception_event_layer_state
time_scope: rolling_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_perception_event_layer
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, perception, input, event-layer]
---

# Perception Event Layer State

## Current Coverage
- status: {report.get('status', 'unknown')}
- checked_at: {report.get('generated_at', 'unknown')}
- event_count: {metrics.get('event_count', 0)}
- source_count: {metrics.get('source_count', 0)}
- event_type_count: {metrics.get('event_type_count', 0)}
- input_event_count: {metrics.get('input_event_count', 0)}
- qq_event_count: {metrics.get('qq_event_count', 0)}
- desktop_event_count: {metrics.get('desktop_event_count', 0)}
- tool_result_event_count: {metrics.get('tool_result_event_count', 0)}
- system_health_event_count: {metrics.get('system_health_event_count', 0)}
- file_change_event_count: {metrics.get('file_change_event_count', 0)}
- visual_event_count: {metrics.get('visual_event_count', 0)}
- voice_event_count: {metrics.get('voice_event_count', 0)}
- multimodal_event_count: {metrics.get('multimodal_event_count', 0)}
- sensory_event_count: {metrics.get('sensory_event_count', 0)}
- importance_ready_count: {metrics.get('importance_ready_count', 0)}
- anomaly_count: {metrics.get('anomaly_count', 0)}
- privacy_scope_count: {metrics.get('privacy_scope_count', 0)}
- latest_event_type: {metrics.get('latest_event_type', 'none')}
- latest_event_source: {metrics.get('latest_event_source', 'none')}
- latest_event_ref: {metrics.get('latest_event_ref', 'none')}

## Boundaries
- report_path: {report_path.as_posix()}
- raw_private_body_retained: false
- visible_reply_text_retained: false
- private_text_in_report: false
- stable_memory_write: blocked
"""
    write_perception_event_layer_state_text(root, text)


def _append_trace(root: Path, report: dict[str, Any]) -> None:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    events = report.get("events") if isinstance(report.get("events"), list) else []
    row = {
        "generated_at": report.get("generated_at", ""),
        "status": report.get("status", ""),
        "ok": bool(report.get("ok")),
        "metrics": metrics,
        "event_refs": [
            {
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "source": event.get("source"),
                "evidence_ref": event.get("evidence_ref"),
                "privacy_scope": event.get("privacy_scope"),
                "anomaly": event.get("anomaly"),
            }
            for event in events[:16]
            if isinstance(event, dict)
        ],
        "raw_private_body_retained": False,
        "visible_reply_text_retained": False,
    }
    append_perception_event_layer_trace_event(root, row)


def _public_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": _one_line(event.get("event_id")),
        "event_type": _one_line(event.get("event_type")),
        "source": _one_line(event.get("source")),
        "observed_at": _one_line(event.get("observed_at")),
        "confidence": _one_line(event.get("confidence")),
        "privacy_scope": _one_line(event.get("privacy_scope")),
        "evidence_ref": _one_line(event.get("evidence_ref")),
        "summary": _one_line(event.get("summary"), limit=180),
        "importance": _one_line(event.get("importance")),
        "anomaly": bool(event.get("anomaly")),
    }


def _dedupe_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for event in events:
        event_id = str(event.get("event_id") or "")
        if not event_id or event_id in seen:
            continue
        seen.add(event_id)
        result.append(event)
    result.sort(key=lambda item: _time_sort_value(item.get("observed_at")))
    return result


def _latest_event(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {}
    dated: list[tuple[float, dict[str, Any]]] = []
    for event in events:
        parsed = _parse_timestamp(event.get("observed_at"))
        if parsed is not None:
            dated.append((_time_sort_value(parsed.isoformat()), event))
    if dated:
        dated.sort(key=lambda item: item[0])
        return dated[-1][1]
    return events[-1]


def _read_jsonl_tail(path: Path, max_lines: int = 500) -> list[dict[str, Any]]:
    return read_perception_event_layer_jsonl_tail(path, max_lines=max_lines)


def _ack_records(path: Path) -> list[dict[str, Any]]:
    rows = _read_jsonl_tail(path, max_lines=500)
    pending_by_key: dict[str, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    for row in rows:
        key = str(row.get("key") or "")
        if row.get("event") == "pending" and key:
            pending_by_key[key] = row
        elif row.get("event") == "acked":
            pending = pending_by_key.get(key, {})
            payload = pending.get("payload") if isinstance(pending.get("payload"), dict) else {}
            records.append(
                {
                    "event_type": "ack",
                    "key": key,
                    "route": row.get("route") or payload.get("route") or "",
                    "observed_at": row.get("acked_at") or "",
                    "adapter_message_id": row.get("adapter_message_id") or payload.get("adapter_message_id") or "",
                    "source_message_id": payload.get("source_message_id") or "",
                    "message_type": payload.get("message_type") or "private",
                }
            )
    return records


def _latest(rows: list[dict[str, Any]], predicate: Any) -> dict[str, Any]:
    for row in reversed(rows):
        try:
            if predicate(row):
                return row
        except (TypeError, ValueError):
            continue
    return {}


def _row_time_text(row: dict[str, Any]) -> str:
    for key in ("recorded_at", "observed_at", "acked_at", "created_at", "sent_at", "checked_at", "updated_at"):
        value = _one_line(row.get(key))
        if value:
            return value
    return ""


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _parse_timestamp(value: Any) -> datetime | None:
    text = _one_line(value).replace("Z", "+00:00")
    if not text or text in NONE_VALUES:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _time_sort_value(value: Any) -> float:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return 0.0
    if parsed.tzinfo is None:
        return parsed.timestamp()
    return parsed.timestamp()


def _present(value: Any) -> bool:
    return _one_line(value).lower() not in NONE_VALUES


def _none_to_empty(value: Any) -> str:
    text = _one_line(value)
    return "" if text.lower() in NONE_VALUES else text


def _count(events: list[dict[str, Any]], event_type: str) -> int:
    return sum(1 for event in events if event.get("event_type") == event_type)


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _result_failed(value: Any) -> bool:
    text = _one_line(value).lower()
    return any(marker in text for marker in ("fail", "error", "timeout", "restart_required", "unhealthy"))


def _ref(value: Any) -> str:
    text = _one_line(value)
    if not text:
        return "none"
    return "sha256:" + _hash(text)[:16]


def _hash(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()


def _clean_token(value: Any, *, default: str) -> str:
    text = _one_line(value).lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_:\-.\u4e00-\u9fff]+", "", text)
    return text or default


def _one_line(value: Any, limit: int = 160) -> str:
    text = " ".join(str(value or "").split())
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("<secret>", text)
    if not text:
        return ""
    return text[: max(1, int(limit))]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build XinYu unified perception event layer.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    report = build_perception_event_layer_report(root)
    if args.write:
        report["written"] = write_perception_event_layer_report(root, report, output=args.output)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_perception_event_layer_report(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
