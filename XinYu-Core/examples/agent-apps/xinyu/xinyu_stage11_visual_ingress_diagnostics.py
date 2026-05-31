from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any


REPORT_REL = Path("worklog") / "xinyu-stage11-visual-ingress-diagnostics-latest.md"
STATE_REL = Path("memory/context/stage11_visual_ingress_diagnostics_state.md")
TRACE_REL = Path("runtime/stage11_visual_ingress_diagnostics_trace.jsonl")

QQ_TRACE_REL = Path("runtime/qq_inbound_trace.jsonl")
QQ_RICH_TRACE_REL = Path("runtime/qq_rich_context_trace.jsonl")
OCR_TRACE_REL = Path("runtime/learning_ocr_trace.jsonl")

VISUAL_COUNT_FIELDS = (
    "image_count",
    "sticker_count",
    "qq_image_count",
    "qq_sticker_count",
)
NONE_VALUES = {"", "missing", "none", "unknown", "null"}
OCR_FAILURE_MARKERS = ("fail", "error", "timeout", "unavailable", "disabled", "missing", "empty")


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


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = _one_line(value, default="").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(value)


def _hash_ref(value: Any) -> str:
    text = _one_line(value, limit=400)
    if not text:
        return "none"
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"sha256:{digest}"


def _read_jsonl_tail(path: Path, *, max_lines: int) -> tuple[list[dict[str, Any]], int]:
    if not path.exists():
        return [], 0
    tail: deque[str] = deque(maxlen=max(1, int(max_lines)))
    total = 0
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for total, line in enumerate(handle, start=1):
                tail.append(line)
    except OSError:
        return [], 0
    rows: list[dict[str, Any]] = []
    for line in tail:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows, total


def _count_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for total, _line in enumerate(handle, start=1):
                pass
    except OSError:
        return 0
    return total


def _row_time_text(row: dict[str, Any]) -> str:
    for key in ("recorded_at", "observed_at", "checked_at", "updated_at", "created_at"):
        text = _one_line(row.get(key), limit=80)
        if text and text.lower() not in NONE_VALUES:
            return text
    return ""


def _visual_count_sum(row: dict[str, Any]) -> int:
    return sum(max(0, _int(row.get(field))) for field in VISUAL_COUNT_FIELDS)


def _has_visual_count_field(row: dict[str, Any]) -> bool:
    names = set(row.keys())
    return any(field in names for field in VISUAL_COUNT_FIELDS)


def _visual_context_notes(row: dict[str, Any]) -> list[str]:
    value = row.get("qq_image_context_notes")
    if not isinstance(value, list):
        return []
    notes: list[str] = []
    for item in value:
        text = _one_line(item, limit=120).strip()
        if text and text not in notes:
            notes.append(text)
    return notes


def _visual_context_requested(row: dict[str, Any]) -> bool:
    return bool(
        _visual_context_notes(row)
        or _bool_value(row.get("qq_image_context_available"))
        or _int(row.get("qq_image_ocr_chars")) > 0
        or _int(row.get("qq_image_vision_chars")) > 0
    )


def _visual_context_available(row: dict[str, Any]) -> bool:
    return (
        _bool_value(row.get("qq_image_context_available"))
        or _int(row.get("qq_image_ocr_chars")) > 0
        or _int(row.get("qq_image_vision_chars")) > 0
    )


def _visual_context_result_ref(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "observed_at": _row_time_text(row) or "unknown",
        "message_kind": _one_line(row.get("message_kind"), limit=80, default="unknown"),
        "stage": _one_line(row.get("stage"), limit=80, default="unknown"),
        "route": _one_line(row.get("route"), limit=80, default="unknown"),
        "visual_count_sum": _visual_count_sum(row),
        "image_context_available": _bool_value(row.get("qq_image_context_available")),
        "ocr_chars": _int(row.get("qq_image_ocr_chars")),
        "vision_chars": _int(row.get("qq_image_vision_chars")),
        "notes": ",".join(_visual_context_notes(row)[:4]) or "none",
        "evidence_ref": _hash_ref(row.get("message_id") or row.get("arrival_seq") or row.get("prepared_seq")),
    }


def _visual_payload_ref(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "observed_at": _row_time_text(row) or "unknown",
        "message_kind": _one_line(row.get("message_kind"), limit=80, default="unknown"),
        "stage": _one_line(row.get("stage"), limit=80, default="unknown"),
        "route": _one_line(row.get("route"), limit=80, default="unknown"),
        "visual_count_sum": _visual_count_sum(row),
        "evidence_ref": _hash_ref(row.get("message_id") or row.get("arrival_seq") or row.get("prepared_seq")),
    }


def _ocr_status(row: dict[str, Any]) -> str:
    return _one_line(row.get("status"), limit=80).strip().lower()


def _ocr_text_len(row: dict[str, Any]) -> int:
    return len(_one_line(row.get("stdout"), limit=4000))


def _ocr_attempted(row: dict[str, Any]) -> bool:
    return bool(_row_time_text(row) or _ocr_status(row) or _ocr_text_len(row) > 0 or str(row.get("returncode", "")).strip())


def _ocr_failed(row: dict[str, Any]) -> bool:
    status = _ocr_status(row)
    returncode = _one_line(row.get("returncode"), limit=24).strip()
    return (
        bool(returncode and returncode not in {"0", "none"})
        or bool(status and any(marker in status for marker in OCR_FAILURE_MARKERS))
    )


def _ocr_succeeded(row: dict[str, Any]) -> bool:
    return _ocr_text_len(row) > 0 and not _ocr_failed(row)


def _status(
    *,
    qq_trace_exists: bool,
    rich_trace_exists: bool,
    visual_field_rows: int,
    visual_payload_rows: int,
    image_context_available_rows: int,
    ocr_result_rows: int,
) -> str:
    if image_context_available_rows > 0 or ocr_result_rows > 0:
        return "connected_interpreted"
    if visual_payload_rows > 0:
        return "connected_payload_only"
    if qq_trace_exists and visual_field_rows > 0:
        return "waiting_for_live_visual_payload"
    if qq_trace_exists or rich_trace_exists:
        return "trace_present_no_visual_fields"
    return "waiting_for_visual_trace_sources"


def _next_step(status: str) -> str:
    if status == "connected_interpreted":
        return "run_stage11_report_and_verify_ready_for_stage12"
    if status == "connected_payload_only":
        return "capture_image_context_or_ocr_result"
    if status == "waiting_for_live_visual_payload":
        return "send_or_capture_real_private_qq_image_message"
    if status == "trace_present_no_visual_fields":
        return "restart_qq_gateway_or_verify_visual_count_trace_version"
    return "connect_qq_image_payload_or_ocr_trace"


def build_stage11_visual_ingress_diagnostics(
    root: Path | str,
    *,
    generated_at: str | None = None,
    max_qq_lines: int = 5000,
) -> dict[str, Any]:
    root = Path(root).resolve()
    generated_at = generated_at or _now_iso()
    qq_path = root / QQ_TRACE_REL
    rich_path = root / QQ_RICH_TRACE_REL
    ocr_path = root / OCR_TRACE_REL
    qq_rows, qq_line_count = _read_jsonl_tail(qq_path, max_lines=max_qq_lines)
    rich_rows, rich_line_count = _read_jsonl_tail(rich_path, max_lines=max_qq_lines)
    ocr_rows, _ocr_tail_total = _read_jsonl_tail(ocr_path, max_lines=200)

    qq_visual_rows = [row for row in qq_rows if _visual_count_sum(row) > 0]
    rich_visual_rows = [row for row in rich_rows if _visual_count_sum(row) > 0]
    visual_payload_rows = qq_visual_rows or rich_visual_rows
    image_context_rows = [row for row in rich_rows if _visual_context_requested(row)]
    image_context_available_rows = [row for row in image_context_rows if _visual_context_available(row)]
    image_context_ocr_rows = [row for row in image_context_rows if _int(row.get("qq_image_ocr_chars")) > 0]
    image_context_vision_rows = [row for row in image_context_rows if _int(row.get("qq_image_vision_chars")) > 0]
    ocr_attempt_rows = [row for row in ocr_rows if _ocr_attempted(row)]
    ocr_result_rows = [row for row in ocr_rows if _ocr_succeeded(row)]
    ocr_error_rows = [row for row in ocr_rows if _ocr_failed(row)]

    latest_visual_payload = visual_payload_rows[-1] if visual_payload_rows else {}
    latest_image_context = image_context_rows[-1] if image_context_rows else {}
    latest_ocr_result = ocr_result_rows[-1] if ocr_result_rows else {}

    visual_field_rows = sum(1 for row in qq_rows if _has_visual_count_field(row)) + sum(
        1 for row in rich_rows if _has_visual_count_field(row)
    )
    status = _status(
        qq_trace_exists=qq_path.exists(),
        rich_trace_exists=rich_path.exists(),
        visual_field_rows=visual_field_rows,
        visual_payload_rows=len(visual_payload_rows),
        image_context_available_rows=len(image_context_available_rows),
        ocr_result_rows=len(ocr_result_rows),
    )

    if image_context_vision_rows:
        evidence_mode = "image_context_vision_summary"
    elif image_context_ocr_rows:
        evidence_mode = "image_context_ocr_text"
    elif ocr_result_rows:
        evidence_mode = "ocr_trace"
    elif visual_payload_rows:
        evidence_mode = "qq_visual_payload_hint"
    else:
        evidence_mode = "none"

    model = {
        "qq_trace_exists": qq_path.exists(),
        "qq_trace_line_count": qq_line_count,
        "qq_scanned_line_count": len(qq_rows),
        "qq_rich_trace_exists": rich_path.exists(),
        "qq_rich_trace_line_count": rich_line_count,
        "qq_rich_scanned_line_count": len(rich_rows),
        "visual_count_field_row_count": visual_field_rows,
        "qq_visual_payload_row_count": len(qq_visual_rows),
        "qq_rich_visual_payload_row_count": len(rich_visual_rows),
        "visual_payload_row_count": len(visual_payload_rows),
        "visual_payload_evidence_ref": _visual_payload_ref(latest_visual_payload).get("evidence_ref", "none")
        if latest_visual_payload
        else "none",
        "visual_payload_latest_observed_at": _row_time_text(latest_visual_payload) if latest_visual_payload else "none",
        "image_context_row_count": len(image_context_rows),
        "image_context_available_count": len(image_context_available_rows),
        "image_context_ocr_result_count": len(image_context_ocr_rows),
        "image_context_vision_result_count": len(image_context_vision_rows),
        "image_context_latest_ref": _visual_context_result_ref(latest_image_context).get("evidence_ref", "none")
        if latest_image_context
        else "none",
        "image_context_latest_observed_at": _row_time_text(latest_image_context) if latest_image_context else "none",
        "image_context_latest_notes": ",".join(_visual_context_notes(latest_image_context)[:4]) if latest_image_context else "none",
        "ocr_trace_exists": ocr_path.exists(),
        "ocr_trace_line_count": _count_jsonl_lines(ocr_path),
        "ocr_attempt_count": len(ocr_attempt_rows),
        "ocr_result_count": len(ocr_result_rows),
        "ocr_error_count": len(ocr_error_rows),
        "ocr_latest_ref": _hash_ref(
            latest_ocr_result.get("path") or latest_ocr_result.get("recorded_at") or latest_ocr_result.get("status")
        )
        if latest_ocr_result
        else "none",
        "ocr_latest_observed_at": _row_time_text(latest_ocr_result) if latest_ocr_result else "none",
        "latest_ocr_text_len": _ocr_text_len(latest_ocr_result) if latest_ocr_result else 0,
        "evidence_mode": evidence_mode,
        "next_step": _next_step(status),
    }
    return {
        "ok": status in {
            "connected_interpreted",
            "connected_payload_only",
            "waiting_for_live_visual_payload",
            "trace_present_no_visual_fields",
        },
        "generated_at": generated_at,
        "root": str(root),
        "stage": "stage11_visual_ingress_diagnostics",
        "status": status,
        "model": model,
        "latest_visual_payload_ref": _visual_payload_ref(latest_visual_payload) if latest_visual_payload else {},
        "latest_image_context_ref": _visual_context_result_ref(latest_image_context) if latest_image_context else {},
        "privacy": {
            "raw_private_body_retained": False,
            "raw_visual_text_retained": False,
            "raw_image_bytes_retained": False,
            "raw_local_path_retained": False,
            "stable_memory_write": "blocked",
            "qq_message_enqueued": False,
            "consciousness_claim": False,
        },
        "evidence_refs": {
            "qq_inbound_trace": QQ_TRACE_REL.as_posix(),
            "qq_rich_context_trace": QQ_RICH_TRACE_REL.as_posix(),
            "ocr_trace": OCR_TRACE_REL.as_posix(),
        },
    }


def render_stage11_visual_ingress_diagnostics(report: dict[str, Any]) -> str:
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    latest_payload = report.get("latest_visual_payload_ref") if isinstance(report.get("latest_visual_payload_ref"), dict) else {}
    latest_context = report.get("latest_image_context_ref") if isinstance(report.get("latest_image_context_ref"), dict) else {}
    lines = [
        "# XinYu Stage 11 Visual Ingress Diagnostics",
        "",
        f"- generated_at: {_one_line(report.get('generated_at'), default='unknown')}",
        f"- status: {_one_line(report.get('status'), default='unknown')}",
        "- claim_boundary: visual ingress evidence only; no consciousness claim",
        "",
        "## Visual Ingress",
    ]
    for key in (
        "qq_trace_exists",
        "qq_trace_line_count",
        "qq_scanned_line_count",
        "qq_rich_trace_exists",
        "qq_rich_trace_line_count",
        "qq_rich_scanned_line_count",
        "visual_count_field_row_count",
        "qq_visual_payload_row_count",
        "qq_rich_visual_payload_row_count",
        "visual_payload_row_count",
        "visual_payload_evidence_ref",
        "visual_payload_latest_observed_at",
        "image_context_row_count",
        "image_context_available_count",
        "image_context_ocr_result_count",
        "image_context_vision_result_count",
        "image_context_latest_ref",
        "image_context_latest_observed_at",
        "image_context_latest_notes",
        "ocr_trace_exists",
        "ocr_trace_line_count",
        "ocr_attempt_count",
        "ocr_result_count",
        "ocr_error_count",
        "ocr_latest_ref",
        "ocr_latest_observed_at",
        "latest_ocr_text_len",
        "evidence_mode",
        "next_step",
    ):
        value = model.get(key, "missing")
        lines.append(f"- {key}: {_bool_text(value) if isinstance(value, bool) else _one_line(value, default='missing')}")
    lines.extend(["", "## Latest Visual Payload Ref"])
    if latest_payload:
        for key in ("observed_at", "message_kind", "stage", "route", "visual_count_sum", "evidence_ref"):
            lines.append(f"- {key}: {_one_line(latest_payload.get(key), default='missing')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Latest Image Context Ref"])
    if latest_context:
        for key in (
            "observed_at",
            "message_kind",
            "stage",
            "route",
            "visual_count_sum",
            "image_context_available",
            "ocr_chars",
            "vision_chars",
            "notes",
            "evidence_ref",
        ):
            value = latest_context.get(key)
            lines.append(f"- {key}: {_bool_text(value) if isinstance(value, bool) else _one_line(value, default='missing')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Privacy Boundary"])
    for key in sorted(privacy):
        value = privacy.get(key)
        lines.append(f"- {key}: {_bool_text(value) if isinstance(value, bool) else _one_line(value, default='missing')}")
    return "\n".join(lines).rstrip() + "\n"


def write_stage11_visual_ingress_diagnostics_report(
    root: Path | str,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> Path:
    root = Path(root).resolve()
    path = output if output is not None else root / REPORT_REL
    if not path.is_absolute():
        path = root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_stage11_visual_ingress_diagnostics(report), encoding="utf-8")
    return path


def write_stage11_visual_ingress_diagnostics_state(
    root: Path | str,
    report: dict[str, Any],
    *,
    report_path: Path | None = None,
) -> Path:
    root = Path(root).resolve()
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    target_report = report_path or (root / REPORT_REL)
    path = root / STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""---
title: Stage 11 Visual Ingress Diagnostics State
memory_type: stage11_visual_ingress_diagnostics_state
time_scope: immediate_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_stage11_visual_ingress_diagnostics
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, multisensory, visual, stage11, audit]
---

# Stage 11 Visual Ingress Diagnostics State

## Gate
- stage11_visual_ingress_status: {report.get('status', 'missing')}
- stage11_visual_ingress_next_step: {model.get('next_step', 'missing')}

## Current Visual Ingress
- stage11_visual_qq_trace_exists: {_bool_text(model.get('qq_trace_exists', False))}
- stage11_visual_qq_trace_line_count: {model.get('qq_trace_line_count', '0')}
- stage11_visual_qq_scanned_line_count: {model.get('qq_scanned_line_count', '0')}
- stage11_visual_qq_rich_trace_exists: {_bool_text(model.get('qq_rich_trace_exists', False))}
- stage11_visual_qq_rich_trace_line_count: {model.get('qq_rich_trace_line_count', '0')}
- stage11_visual_count_field_row_count: {model.get('visual_count_field_row_count', '0')}
- stage11_visual_payload_row_count: {model.get('visual_payload_row_count', '0')}
- stage11_visual_payload_evidence_ref: {model.get('visual_payload_evidence_ref', 'none')}
- stage11_visual_payload_latest_observed_at: {model.get('visual_payload_latest_observed_at', 'none')}
- stage11_visual_image_context_row_count: {model.get('image_context_row_count', '0')}
- stage11_visual_image_context_available_count: {model.get('image_context_available_count', '0')}
- stage11_visual_image_context_ocr_result_count: {model.get('image_context_ocr_result_count', '0')}
- stage11_visual_image_context_vision_result_count: {model.get('image_context_vision_result_count', '0')}
- stage11_visual_image_context_latest_ref: {model.get('image_context_latest_ref', 'none')}
- stage11_visual_image_context_latest_observed_at: {model.get('image_context_latest_observed_at', 'none')}
- stage11_visual_image_context_latest_notes: {model.get('image_context_latest_notes', 'none')}
- stage11_visual_ocr_trace_exists: {_bool_text(model.get('ocr_trace_exists', False))}
- stage11_visual_ocr_trace_line_count: {model.get('ocr_trace_line_count', '0')}
- stage11_visual_ocr_attempt_count: {model.get('ocr_attempt_count', '0')}
- stage11_visual_ocr_result_count: {model.get('ocr_result_count', '0')}
- stage11_visual_ocr_error_count: {model.get('ocr_error_count', '0')}
- stage11_visual_ocr_latest_ref: {model.get('ocr_latest_ref', 'none')}
- stage11_visual_ocr_latest_observed_at: {model.get('ocr_latest_observed_at', 'none')}
- stage11_visual_evidence_mode: {model.get('evidence_mode', 'none')}

## Boundaries
- raw_private_body_retained: {_bool_text(privacy.get('raw_private_body_retained', False))}
- raw_visual_text_retained: {_bool_text(privacy.get('raw_visual_text_retained', False))}
- raw_image_bytes_retained: {_bool_text(privacy.get('raw_image_bytes_retained', False))}
- raw_local_path_retained: {_bool_text(privacy.get('raw_local_path_retained', False))}
- stable_memory_write: {privacy.get('stable_memory_write', 'blocked')}
- qq_message_enqueued: {_bool_text(privacy.get('qq_message_enqueued', False))}
- consciousness_claim: {_bool_text(privacy.get('consciousness_claim', False))}
- report_path: {target_report.as_posix()}
"""
    path.write_text(text, encoding="utf-8")
    return path


def append_stage11_visual_ingress_diagnostics_trace(root: Path | str, report: dict[str, Any]) -> Path:
    root = Path(root).resolve()
    model = report.get("model") if isinstance(report.get("model"), dict) else {}
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "observed_at": report.get("generated_at", _now_iso()),
        "status": report.get("status", "missing"),
        "visual_payload_row_count": model.get("visual_payload_row_count", "0"),
        "image_context_available_count": model.get("image_context_available_count", "0"),
        "image_context_vision_result_count": model.get("image_context_vision_result_count", "0"),
        "image_context_ocr_result_count": model.get("image_context_ocr_result_count", "0"),
        "ocr_result_count": model.get("ocr_result_count", "0"),
        "ocr_error_count": model.get("ocr_error_count", "0"),
        "visual_count_field_row_count": model.get("visual_count_field_row_count", "0"),
        "evidence_mode": model.get("evidence_mode", "none"),
        "next_step": model.get("next_step", "missing"),
        "raw_private_body_retained": False,
        "raw_visual_text_retained": False,
        "raw_image_bytes_retained": False,
        "qq_message_enqueued": False,
        "consciousness_claim": False,
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose XinYu Stage 11 visual ingress.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--max-qq-lines", type=int, default=5000)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_stage11_visual_ingress_diagnostics(args.root, max_qq_lines=args.max_qq_lines)
    if args.write:
        report_path = write_stage11_visual_ingress_diagnostics_report(args.root, report, output=args.output)
        state_path = write_stage11_visual_ingress_diagnostics_state(args.root, report, report_path=report_path)
        trace_path = append_stage11_visual_ingress_diagnostics_trace(args.root, report)
        report["report_path"] = str(report_path)
        report["state_path"] = str(state_path)
        report["trace_path"] = str(trace_path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_stage11_visual_ingress_diagnostics(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
