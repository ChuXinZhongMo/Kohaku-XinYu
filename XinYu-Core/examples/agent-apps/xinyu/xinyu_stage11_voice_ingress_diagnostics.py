from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_stage11_voice_ingress_diagnostics_store import QQ_RICH_TRACE_REL
from xinyu_stage11_voice_ingress_diagnostics_store import QQ_TRACE_REL
from xinyu_stage11_voice_ingress_diagnostics_store import REPORT_REL
from xinyu_stage11_voice_ingress_diagnostics_store import VOICE_TRACE_RELS
from xinyu_stage11_voice_ingress_diagnostics_store import append_stage11_voice_trace_event
from xinyu_stage11_voice_ingress_diagnostics_store import read_stage11_voice_jsonl_tail
from xinyu_stage11_voice_ingress_diagnostics_store import read_stage11_voice_transcript_rows
from xinyu_stage11_voice_ingress_diagnostics_store import stage11_voice_qq_rich_trace_path
from xinyu_stage11_voice_ingress_diagnostics_store import stage11_voice_qq_trace_path
from xinyu_stage11_voice_ingress_diagnostics_store import write_stage11_voice_report_text
from xinyu_stage11_voice_ingress_diagnostics_store import write_stage11_voice_state_text

VOICE_COUNT_FIELDS = (
    "voice_count",
    "audio_count",
    "record_count",
    "qq_voice_count",
    "qq_audio_count",
    "qq_record_count",
)
VOICE_SEGMENT_TYPES = {"record", "voice", "audio"}
VOICE_SUMMARY_MARKERS = (
    "voice",
    "audio",
    "record",
    "voice_audio",
    "\u8bed\u97f3",
    "\u97f3\u9891",
    "\u7487",
    "\u95ca",
)
NONE_VALUES = {"", "missing", "none", "unknown", "null"}
TRANSCRIPT_SUCCESS_STATUSES = {"transcribed", "completed", "ok"}
TRANSCRIPT_FAILURE_MARKERS = ("fail", "error", "timeout", "unavailable", "disabled", "missing", "empty")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _one_line(value: Any, *, limit: int = 180, default: str = "") -> str:
    text = "" if value is None else " ".join(str(value).split())
    if not text:
        return default
    text = re.sub(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+", "<local_path>", text)
    text = re.sub(r"(?i)\b(?:authorization|api[_-]?key|token|password|cookie)\s*[:=]\s*[^\s<>'\"]+", "<secret>", text)
    text = re.sub(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)\bsk-[a-z0-9_-]{12,}", "<secret>", text)
    return text[: max(1, int(limit))]


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _hash_ref(value: Any) -> str:
    text = _one_line(value, limit=400)
    if not text:
        return "none"
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"sha256:{digest}"


def _row_time_text(row: dict[str, Any]) -> str:
    for key in ("recorded_at", "observed_at", "checked_at", "updated_at", "created_at"):
        text = _one_line(row.get(key), limit=80)
        if text and text.lower() not in NONE_VALUES:
            return text
    return ""


def _voice_count_sum(row: dict[str, Any]) -> int:
    return sum(max(0, _int(row.get(field))) for field in VOICE_COUNT_FIELDS)


def _has_voice_count_field(row: dict[str, Any]) -> bool:
    names = set(row.keys())
    return any(field in names for field in VOICE_COUNT_FIELDS)


def _summary_has_voice_hint(row: dict[str, Any]) -> bool:
    parts = [
        _one_line(row.get("rich_summary"), limit=500),
        _one_line(row.get("qq_rich_summary"), limit=500),
        _one_line(row.get("summary"), limit=500),
    ]
    text = " ".join(parts).lower()
    if not text:
        return False
    return any(marker in text for marker in VOICE_SUMMARY_MARKERS)


def _segments_have_voice_hint(row: dict[str, Any]) -> bool:
    segments = row.get("segments") or row.get("qq_message_segments")
    if not isinstance(segments, list):
        return False
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        kind = _one_line(segment.get("kind"), limit=40).lower()
        segment_type = _one_line(segment.get("segment_type") or segment.get("type"), limit=40).lower()
        if kind == "voice" or segment_type in VOICE_SEGMENT_TYPES:
            return True
    return False


def _row_has_voice_payload(row: dict[str, Any]) -> bool:
    return _voice_count_sum(row) > 0 or _summary_has_voice_hint(row) or _segments_have_voice_hint(row)


def _transcript_len(row: dict[str, Any]) -> int:
    text = (
        _one_line(row.get("transcript"), limit=4000)
        or _one_line(row.get("transcript_text"), limit=4000)
        or _one_line(row.get("text"), limit=4000)
        or _one_line(row.get("stdout"), limit=4000)
    )
    return len(text)


def _transcript_status(row: dict[str, Any]) -> str:
    return _one_line(row.get("status") or row.get("event_kind"), limit=80).strip().lower()


def _transcript_attempted(row: dict[str, Any]) -> bool:
    return bool(_row_time_text(row) or _transcript_len(row) > 0 or _transcript_status(row))


def _transcript_succeeded(row: dict[str, Any]) -> bool:
    status = _transcript_status(row)
    if status and any(marker in status for marker in TRANSCRIPT_FAILURE_MARKERS):
        return False
    if status and status not in TRANSCRIPT_SUCCESS_STATUSES and _transcript_len(row) <= 0:
        return False
    return _transcript_len(row) > 0


def _transcript_failed(row: dict[str, Any]) -> bool:
    status = _transcript_status(row)
    return bool(status and any(marker in status for marker in TRANSCRIPT_FAILURE_MARKERS))


def _voice_like_ref(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "observed_at": _row_time_text(row) or "unknown",
        "message_kind": _one_line(row.get("message_kind") or row.get("message_type"), limit=80, default="unknown"),
        "stage": _one_line(row.get("stage"), limit=80, default="unknown"),
        "route": _one_line(row.get("route"), limit=80, default="unknown"),
        "voice_count_sum": _voice_count_sum(row),
        "evidence_ref": _hash_ref(row.get("message_id") or row.get("arrival_seq") or row.get("event_id")),
    }


def _status(*, qq_trace_exists: bool, voice_field_rows: int, qq_voice_rows: int, transcript_rows: int) -> str:
    if qq_voice_rows > 0 or transcript_rows > 0:
        return "connected"
    if qq_trace_exists and voice_field_rows > 0:
        return "waiting_for_live_voice_payload"
    if qq_trace_exists:
        return "trace_present_no_voice_fields"
    return "waiting_for_voice_trace_sources"


def _next_step(status: str) -> str:
    if status == "connected":
        return "run_stage11_report_and_verify_ready_for_stage12"
    if status == "waiting_for_live_voice_payload":
        return "send_or_capture_real_private_qq_voice_message"
    if status == "trace_present_no_voice_fields":
        return "restart_qq_gateway_or_verify_voice_count_trace_version"
    return "connect_qq_voice_payload_or_voice_transcript_trace"


def build_stage11_voice_ingress_diagnostics(
    root: Path | str,
    *,
    generated_at: str | None = None,
    max_qq_lines: int = 5000,
) -> dict[str, Any]:
    root = Path(root).resolve()
    generated_at = generated_at or _now_iso()
    qq_path = stage11_voice_qq_trace_path(root)
    rich_path = stage11_voice_qq_rich_trace_path(root)
    qq_rows, qq_line_count = read_stage11_voice_jsonl_tail(qq_path, max_lines=max_qq_lines)
    rich_rows, rich_line_count = read_stage11_voice_jsonl_tail(rich_path, max_lines=max_qq_lines)
    transcript_rows, transcript_file_count, transcript_line_count = read_stage11_voice_transcript_rows(root)

    qq_voice_rows = [row for row in qq_rows if _row_has_voice_payload(row)]
    rich_voice_rows = [row for row in rich_rows if _row_has_voice_payload(row)]
    voice_payload_rows = qq_voice_rows or rich_voice_rows
    transcript_attempt_rows = [row for row in transcript_rows if _transcript_attempted(row)]
    transcript_result_rows = [row for row in transcript_rows if _transcript_succeeded(row)]
    transcript_error_rows = [row for row in transcript_rows if _transcript_failed(row)]
    latest_voice_payload = voice_payload_rows[-1] if voice_payload_rows else {}
    latest_transcript = transcript_result_rows[-1] if transcript_result_rows else {}
    latest_transcript_attempt = transcript_attempt_rows[-1] if transcript_attempt_rows else {}
    voice_field_rows = sum(1 for row in qq_rows if _has_voice_count_field(row)) + sum(
        1 for row in rich_rows if _has_voice_count_field(row)
    )
    status = _status(
        qq_trace_exists=qq_path.exists() or rich_path.exists(),
        voice_field_rows=voice_field_rows,
        qq_voice_rows=len(voice_payload_rows),
        transcript_rows=len(transcript_result_rows),
    )
    model = {
        "qq_trace_exists": qq_path.exists(),
        "qq_trace_line_count": qq_line_count,
        "qq_scanned_line_count": len(qq_rows),
        "qq_rich_trace_exists": rich_path.exists(),
        "qq_rich_trace_line_count": rich_line_count,
        "qq_rich_scanned_line_count": len(rich_rows),
        "voice_count_field_row_count": voice_field_rows,
        "qq_voice_payload_row_count": len(qq_voice_rows),
        "qq_rich_voice_payload_row_count": len(rich_voice_rows),
        "voice_payload_row_count": len(voice_payload_rows),
        "voice_payload_evidence_ref": _voice_like_ref(latest_voice_payload).get("evidence_ref", "none")
        if latest_voice_payload
        else "none",
        "voice_payload_latest_observed_at": _row_time_text(latest_voice_payload) if latest_voice_payload else "none",
        "voice_transcript_trace_file_count": transcript_file_count,
        "voice_transcript_trace_line_count": transcript_line_count,
        "voice_transcript_attempt_count": len(transcript_attempt_rows),
        "voice_transcript_result_count": len(transcript_result_rows),
        "voice_transcript_error_count": len(transcript_error_rows),
        "voice_transcript_latest_ref": _hash_ref(
            latest_transcript.get("event_id") or latest_transcript.get("message_id") or _row_time_text(latest_transcript)
        )
        if latest_transcript
        else "none",
        "voice_transcript_latest_observed_at": _row_time_text(latest_transcript) if latest_transcript else "none",
        "voice_transcript_latest_attempt_ref": _hash_ref(
            latest_transcript_attempt.get("event_id")
            or latest_transcript_attempt.get("message_id")
            or _row_time_text(latest_transcript_attempt)
        )
        if latest_transcript_attempt
        else "none",
        "voice_transcript_latest_attempt_status": _transcript_status(latest_transcript_attempt)
        if latest_transcript_attempt
        else "none",
        "latest_transcript_len": _transcript_len(latest_transcript) if latest_transcript else 0,
        "evidence_mode": "transcript_trace"
        if transcript_result_rows
        else "qq_voice_payload_hint"
        if voice_payload_rows
        else "none",
        "next_step": _next_step(status),
    }
    return {
        "ok": status in {"connected", "waiting_for_live_voice_payload", "trace_present_no_voice_fields"},
        "generated_at": generated_at,
        "root": str(root),
        "stage": "stage11_voice_ingress_diagnostics",
        "status": status,
        "model": model,
        "latest_voice_payload_ref": _voice_like_ref(latest_voice_payload) if latest_voice_payload else {},
        "privacy": {
            "raw_private_body_retained": False,
            "raw_voice_transcript_retained": False,
            "raw_audio_bytes_retained": False,
            "raw_audio_path_retained": False,
            "stable_memory_write": "blocked",
            "qq_message_enqueued": False,
            "consciousness_claim": False,
        },
        "evidence_refs": {
            "qq_inbound_trace": QQ_TRACE_REL.as_posix(),
            "qq_rich_context_trace": QQ_RICH_TRACE_REL.as_posix(),
            "voice_trace_candidates": ",".join(rel.as_posix() for rel in VOICE_TRACE_RELS),
        },
    }


def render_stage11_voice_ingress_diagnostics(report: dict[str, Any]) -> str:
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    latest = report.get("latest_voice_payload_ref") if isinstance(report.get("latest_voice_payload_ref"), dict) else {}
    lines = [
        "# XinYu Stage 11 Voice Ingress Diagnostics",
        "",
        f"- generated_at: {_one_line(report.get('generated_at'), default='unknown')}",
        f"- status: {_one_line(report.get('status'), default='unknown')}",
        "- claim_boundary: voice ingress evidence only; no consciousness claim",
        "",
        "## Voice Ingress",
    ]
    for key in (
        "qq_trace_exists",
        "qq_trace_line_count",
        "qq_scanned_line_count",
        "qq_rich_trace_exists",
        "qq_rich_trace_line_count",
        "qq_rich_scanned_line_count",
        "voice_count_field_row_count",
        "qq_voice_payload_row_count",
        "qq_rich_voice_payload_row_count",
        "voice_payload_row_count",
        "voice_payload_evidence_ref",
        "voice_payload_latest_observed_at",
        "voice_transcript_trace_file_count",
        "voice_transcript_trace_line_count",
        "voice_transcript_attempt_count",
        "voice_transcript_result_count",
        "voice_transcript_error_count",
        "voice_transcript_latest_ref",
        "voice_transcript_latest_observed_at",
        "voice_transcript_latest_attempt_ref",
        "voice_transcript_latest_attempt_status",
        "latest_transcript_len",
        "evidence_mode",
        "next_step",
    ):
        value = model.get(key, "missing")
        lines.append(f"- {key}: {_bool_text(value) if isinstance(value, bool) else _one_line(value, default='missing')}")
    lines.extend(["", "## Latest Voice Payload Ref"])
    if latest:
        for key in ("observed_at", "message_kind", "stage", "route", "voice_count_sum", "evidence_ref"):
            lines.append(f"- {key}: {_one_line(latest.get(key), default='missing')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Privacy Boundary"])
    for key in sorted(privacy):
        value = privacy.get(key)
        lines.append(f"- {key}: {_bool_text(value) if isinstance(value, bool) else _one_line(value, default='missing')}")
    return "\n".join(lines).rstrip() + "\n"


def write_stage11_voice_ingress_diagnostics_report(
    root: Path | str,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> Path:
    root = Path(root).resolve()
    return write_stage11_voice_report_text(root, render_stage11_voice_ingress_diagnostics(report), output=output)


def write_stage11_voice_ingress_diagnostics_state(
    root: Path | str,
    report: dict[str, Any],
    *,
    report_path: Path | None = None,
) -> Path:
    root = Path(root).resolve()
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    target_report = report_path or (root / REPORT_REL)
    text = f"""---
title: Stage 11 Voice Ingress Diagnostics State
memory_type: stage11_voice_ingress_diagnostics_state
time_scope: immediate_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_stage11_voice_ingress_diagnostics
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, multisensory, voice, stage11, audit]
---

# Stage 11 Voice Ingress Diagnostics State

## Gate
- stage11_voice_ingress_status: {report.get('status', 'missing')}
- stage11_voice_ingress_next_step: {model.get('next_step', 'missing')}

## Current Voice Ingress
- stage11_voice_qq_trace_exists: {_bool_text(model.get('qq_trace_exists', False))}
- stage11_voice_qq_trace_line_count: {model.get('qq_trace_line_count', '0')}
- stage11_voice_qq_scanned_line_count: {model.get('qq_scanned_line_count', '0')}
- stage11_voice_qq_rich_trace_exists: {_bool_text(model.get('qq_rich_trace_exists', False))}
- stage11_voice_qq_rich_trace_line_count: {model.get('qq_rich_trace_line_count', '0')}
- stage11_voice_count_field_row_count: {model.get('voice_count_field_row_count', '0')}
- stage11_voice_payload_row_count: {model.get('voice_payload_row_count', '0')}
- stage11_voice_payload_evidence_ref: {model.get('voice_payload_evidence_ref', 'none')}
- stage11_voice_payload_latest_observed_at: {model.get('voice_payload_latest_observed_at', 'none')}
- stage11_voice_transcript_trace_file_count: {model.get('voice_transcript_trace_file_count', '0')}
- stage11_voice_transcript_trace_line_count: {model.get('voice_transcript_trace_line_count', '0')}
- stage11_voice_transcript_attempt_count: {model.get('voice_transcript_attempt_count', '0')}
- stage11_voice_transcript_result_count: {model.get('voice_transcript_result_count', '0')}
- stage11_voice_transcript_error_count: {model.get('voice_transcript_error_count', '0')}
- stage11_voice_transcript_latest_ref: {model.get('voice_transcript_latest_ref', 'none')}
- stage11_voice_transcript_latest_observed_at: {model.get('voice_transcript_latest_observed_at', 'none')}
- stage11_voice_transcript_latest_attempt_ref: {model.get('voice_transcript_latest_attempt_ref', 'none')}
- stage11_voice_transcript_latest_attempt_status: {model.get('voice_transcript_latest_attempt_status', 'none')}
- stage11_voice_evidence_mode: {model.get('evidence_mode', 'none')}

## Boundaries
- raw_private_body_retained: {_bool_text(privacy.get('raw_private_body_retained', False))}
- raw_voice_transcript_retained: {_bool_text(privacy.get('raw_voice_transcript_retained', False))}
- raw_audio_bytes_retained: {_bool_text(privacy.get('raw_audio_bytes_retained', False))}
- raw_audio_path_retained: {_bool_text(privacy.get('raw_audio_path_retained', False))}
- stable_memory_write: {privacy.get('stable_memory_write', 'blocked')}
- qq_message_enqueued: {_bool_text(privacy.get('qq_message_enqueued', False))}
- consciousness_claim: {_bool_text(privacy.get('consciousness_claim', False))}
- report_path: {target_report.as_posix()}
"""
    return write_stage11_voice_state_text(root, text)


def append_stage11_voice_ingress_diagnostics_trace(root: Path | str, report: dict[str, Any]) -> Path:
    root = Path(root).resolve()
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    row = {
        "observed_at": report.get("generated_at", _now_iso()),
        "status": report.get("status", "missing"),
        "voice_payload_row_count": model.get("voice_payload_row_count", "0"),
        "voice_transcript_attempt_count": model.get("voice_transcript_attempt_count", "0"),
        "voice_transcript_result_count": model.get("voice_transcript_result_count", "0"),
        "voice_transcript_error_count": model.get("voice_transcript_error_count", "0"),
        "voice_count_field_row_count": model.get("voice_count_field_row_count", "0"),
        "evidence_mode": model.get("evidence_mode", "none"),
        "next_step": model.get("next_step", "missing"),
        "raw_private_body_retained": False,
        "raw_voice_transcript_retained": False,
        "raw_audio_bytes_retained": False,
        "qq_message_enqueued": False,
        "consciousness_claim": False,
    }
    return append_stage11_voice_trace_event(root, row)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose XinYu Stage 11 voice ingress.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--max-qq-lines", type=int, default=5000)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_stage11_voice_ingress_diagnostics(args.root, max_qq_lines=args.max_qq_lines)
    if args.write:
        report_path = write_stage11_voice_ingress_diagnostics_report(args.root, report, output=args.output)
        state_path = write_stage11_voice_ingress_diagnostics_state(args.root, report, report_path=report_path)
        trace_path = append_stage11_voice_ingress_diagnostics_trace(args.root, report)
        report["report_path"] = str(report_path)
        report["state_path"] = str(state_path)
        report["trace_path"] = str(trace_path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_stage11_voice_ingress_diagnostics(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
