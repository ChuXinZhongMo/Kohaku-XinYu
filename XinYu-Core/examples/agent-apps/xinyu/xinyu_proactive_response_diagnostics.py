from __future__ import annotations


__all__ = (
    "PROACTIVE_DISPATCH_STATE_REL",
    "PROACTIVE_REQUEST_STATE_REL",
    "REPORT_REL",
    "TRACE_REL",
)

import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from xinyu_proactive_response_diagnostics_store import STATE_REL
from xinyu_proactive_response_diagnostics_store import append_proactive_response_diagnostics_trace_event
from xinyu_proactive_response_diagnostics_store import read_proactive_dispatch_state_text
from xinyu_proactive_response_diagnostics_store import read_proactive_request_state_text
from xinyu_proactive_response_diagnostics_store import write_proactive_response_diagnostics_report_text
from xinyu_proactive_response_diagnostics_store import write_proactive_response_diagnostics_state_text

from xinyu_proactive_response_diagnostics_store import PROACTIVE_DISPATCH_STATE_REL

from xinyu_action_feedback_coverage import PROACTIVE_REQUEST_STATE_REL

from xinyu_action_feedback_coverage import REPORT_REL

from xinyu_action_feedback_coverage import TRACE_REL

OWNER_NO_RESPONSE_TIMEOUT_MINUTES = 180
NONE_VALUES = {"", "missing", "none", "unknown", "null"}
WAITING_ANSWER_STATES = {
    "pending",
    "sent_waiting_owner_reply",
    "waiting_owner_reply",
    "sent_waiting_feedback",
}
DELIVERED_ACK_STATES = {"sent", "queued", "delivered", "acked", "success"}
RESPONSE_SIGNAL_BY_ANSWER_STATE = {
    "read_locally": "desktop_read_locally",
    "read_local": "desktop_read_locally",
    "read": "desktop_read_locally",
    "dismiss": "desktop_dismissed",
    "dismissed": "desktop_dismissed",
    "reply": "desktop_owner_replied",
    "replied": "desktop_owner_replied",
    "answered": "desktop_owner_replied",
    "owner_replied": "desktop_owner_replied",
    "approve_qq": "desktop_approved_qq",
    "approved_qq": "desktop_approved_qq",
    "approved": "desktop_approved_qq",
}


def build_proactive_response_diagnostics(root: Path, *, generated_at: str | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    generated_at = generated_at or _now_iso()
    request = _parse_fields(read_proactive_request_state_text(root))
    dispatch = _parse_fields(read_proactive_dispatch_state_text(root))
    if not request:
        return _empty_report(root, generated_at)

    request_status = _one_line(request.get("status"), "missing")
    answer_state = _one_line(request.get("request_answer_state"), "missing").lower()
    last_ack_status = _one_line(
        request.get("last_ack_status") or dispatch.get("last_ack_status"),
        "missing",
    ).lower()
    adapter_error = _one_line(
        request.get("adapter_error") or dispatch.get("adapter_error"),
        "none",
        limit=160,
    )
    delivered_waiting_owner = answer_state in WAITING_ANSWER_STATES and last_ack_status in DELIVERED_ACK_STATES
    reference_time = _reference_time(request, dispatch)
    age_minutes = _age_minutes(reference_time, generated_at)
    timeout_active = (
        delivered_waiting_owner
        and age_minutes is not None
        and age_minutes >= OWNER_NO_RESPONSE_TIMEOUT_MINUTES
    )
    minutes_until_timeout = _minutes_until_timeout(age_minutes, delivered_waiting_owner)
    next_timeout_at = _next_timeout_at(reference_time, delivered_waiting_owner)
    response_signal = _response_signal(
        answer_state=answer_state,
        last_ack_status=last_ack_status,
        adapter_error=adapter_error,
        delivered_waiting_owner=delivered_waiting_owner,
        timeout_active=timeout_active,
    )
    status = _status_for(
        response_signal=response_signal,
        delivered_waiting_owner=delivered_waiting_owner,
        request_status=request_status,
    )
    report = {
        "ok": True,
        "status": status,
        "generated_at": generated_at,
        "root": str(root),
        "request_status": request_status,
        "request_answer_state": answer_state,
        "last_ack_status": last_ack_status,
        "delivery_level": _one_line(request.get("delivery_level"), "missing"),
        "response_signal_candidate": response_signal,
        "delivered_waiting_owner": delivered_waiting_owner,
        "timeout_active": timeout_active,
        "timeout_minutes": OWNER_NO_RESPONSE_TIMEOUT_MINUTES,
        "age_minutes": _format_minutes(age_minutes),
        "minutes_until_no_response_timeout": minutes_until_timeout,
        "next_no_response_timeout_at": next_timeout_at,
        "request_event_ref": _content_ref(
            request.get("request_id")
            or request.get("thread_id")
            or request.get("evidence_hash")
            or request.get("created_at")
        ),
        "future_effect_if_timeout": (
            "lower_active_request_frequency_until_new_owner_evidence"
            if timeout_active or delivered_waiting_owner
            else "none"
        ),
        "source_snapshot": {
            "request_id_ref": _content_ref(request.get("request_id")),
            "thread_ref": _content_ref(request.get("thread_id")),
            "created_at": _one_line(request.get("created_at"), "missing"),
            "last_acked_at": _one_line(request.get("last_acked_at") or dispatch.get("last_acked_at"), "missing"),
            "updated_at": _one_line(request.get("updated_at"), "missing"),
            "adapter_error_present": _present(adapter_error),
        },
        "privacy": {
            "raw_owner_text_retained": False,
            "request_body_text_retained": False,
            "visible_reply_text_retained": False,
            "state_contains_refs_and_status_only": True,
        },
        "notes": _notes(response_signal, delivered_waiting_owner, timeout_active),
    }
    return report


def write_proactive_response_diagnostics(
    root: Path,
    report: dict[str, Any],
    *,
    output: Path | None = None,
    write_report: bool = True,
) -> dict[str, str]:
    root = Path(root).resolve()
    paths: dict[str, str] = {}
    if write_report:
        report_path = write_proactive_response_diagnostics_report_text(
            root,
            render_proactive_response_diagnostics(report),
            output=output,
        )
        paths["report_path"] = str(report_path)
    _write_state(root, report, report_path=paths.get("report_path", "not_written"))
    _append_trace(root, report)
    paths["state_path"] = str(root / STATE_REL)
    return paths


def render_proactive_response_diagnostics(report: dict[str, Any]) -> str:
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    source = report.get("source_snapshot") if isinstance(report.get("source_snapshot"), dict) else {}
    lines = [
        "# XinYu Proactive Response Diagnostics",
        "",
        f"- generated_at: {report.get('generated_at', 'unknown')}",
        f"- status: {report.get('status', 'unknown')}",
        f"- result: {'pass' if report.get('ok') else 'needs_check'}",
        "- claim_boundary: diagnostics for pending proactive owner response only; no consciousness claim",
        "",
        "## Current Request Feedback",
        f"- request_status: {report.get('request_status', 'missing')}",
        f"- request_answer_state: {report.get('request_answer_state', 'missing')}",
        f"- last_ack_status: {report.get('last_ack_status', 'missing')}",
        f"- delivery_level: {report.get('delivery_level', 'missing')}",
        f"- response_signal_candidate: {report.get('response_signal_candidate', 'none')}",
        f"- delivered_waiting_owner: {str(report.get('delivered_waiting_owner', False)).lower()}",
        f"- timeout_active: {str(report.get('timeout_active', False)).lower()}",
        f"- timeout_minutes: {report.get('timeout_minutes', OWNER_NO_RESPONSE_TIMEOUT_MINUTES)}",
        f"- age_minutes: {report.get('age_minutes', 'unknown')}",
        f"- minutes_until_no_response_timeout: {report.get('minutes_until_no_response_timeout', 'unknown')}",
        f"- next_no_response_timeout_at: {report.get('next_no_response_timeout_at', 'none')}",
        f"- future_effect_if_timeout: {report.get('future_effect_if_timeout', 'none')}",
        f"- request_event_ref: {report.get('request_event_ref', 'none')}",
        "",
        "## Source Snapshot",
    ]
    for key in ("request_id_ref", "thread_ref", "created_at", "last_acked_at", "updated_at", "adapter_error_present"):
        lines.append(f"- {key}: {source.get(key, 'missing')}")
    lines.extend(["", "## Privacy Boundary"])
    for key, value in privacy.items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Notes"])
    notes = report.get("notes") if isinstance(report.get("notes"), list) else []
    lines.extend(f"- {note}" for note in notes) if notes else lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def _empty_report(root: Path, generated_at: str) -> dict[str, Any]:
    return {
        "ok": True,
        "status": "no_request",
        "generated_at": generated_at,
        "root": str(root),
        "request_status": "missing",
        "request_answer_state": "missing",
        "last_ack_status": "missing",
        "delivery_level": "missing",
        "response_signal_candidate": "none",
        "delivered_waiting_owner": False,
        "timeout_active": False,
        "timeout_minutes": OWNER_NO_RESPONSE_TIMEOUT_MINUTES,
        "age_minutes": "unknown",
        "minutes_until_no_response_timeout": "none",
        "next_no_response_timeout_at": "none",
        "request_event_ref": "none",
        "future_effect_if_timeout": "none",
        "source_snapshot": {
            "request_id_ref": "none",
            "thread_ref": "none",
            "created_at": "missing",
            "last_acked_at": "missing",
            "updated_at": "missing",
            "adapter_error_present": False,
        },
        "privacy": {
            "raw_owner_text_retained": False,
            "request_body_text_retained": False,
            "visible_reply_text_retained": False,
            "state_contains_refs_and_status_only": True,
        },
        "notes": ["no_proactive_request_state"],
    }


def _write_state(root: Path, report: dict[str, Any], *, report_path: str) -> None:
    text = f"""---
title: Proactive Response Diagnostics State
memory_type: proactive_response_diagnostics_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_proactive_response_diagnostics
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [proactive, owner-response, diagnostics, feedback]
---

# Proactive Response Diagnostics State

## Current Request Feedback
- status: {report.get('status', 'unknown')}
- checked_at: {report.get('generated_at', 'unknown')}
- request_status: {report.get('request_status', 'missing')}
- request_answer_state: {report.get('request_answer_state', 'missing')}
- last_ack_status: {report.get('last_ack_status', 'missing')}
- delivery_level: {report.get('delivery_level', 'missing')}
- response_signal_candidate: {report.get('response_signal_candidate', 'none')}
- delivered_waiting_owner: {str(report.get('delivered_waiting_owner', False)).lower()}
- timeout_active: {str(report.get('timeout_active', False)).lower()}
- timeout_minutes: {report.get('timeout_minutes', OWNER_NO_RESPONSE_TIMEOUT_MINUTES)}
- age_minutes: {report.get('age_minutes', 'unknown')}
- minutes_until_no_response_timeout: {report.get('minutes_until_no_response_timeout', 'unknown')}
- next_no_response_timeout_at: {report.get('next_no_response_timeout_at', 'none')}
- future_effect_if_timeout: {report.get('future_effect_if_timeout', 'none')}
- request_event_ref: {report.get('request_event_ref', 'none')}

## Boundaries
- report_path: {report_path}
- raw_owner_text_retained: false
- request_body_text_retained: false
- visible_reply_text_retained: false
- state_contains_refs_and_status_only: true
"""
    write_proactive_response_diagnostics_state_text(root, text)


def _append_trace(root: Path, report: dict[str, Any]) -> None:
    row = {
        "generated_at": report.get("generated_at", ""),
        "status": report.get("status", ""),
        "ok": bool(report.get("ok")),
        "request_status": report.get("request_status", "missing"),
        "request_answer_state": report.get("request_answer_state", "missing"),
        "last_ack_status": report.get("last_ack_status", "missing"),
        "response_signal_candidate": report.get("response_signal_candidate", "none"),
        "delivered_waiting_owner": bool(report.get("delivered_waiting_owner")),
        "timeout_active": bool(report.get("timeout_active")),
        "age_minutes": report.get("age_minutes", "unknown"),
        "minutes_until_no_response_timeout": report.get("minutes_until_no_response_timeout", "unknown"),
        "request_event_ref": report.get("request_event_ref", "none"),
        "raw_owner_text_retained": False,
        "request_body_text_retained": False,
        "visible_reply_text_retained": False,
    }
    append_proactive_response_diagnostics_trace_event(root, row)


def _response_signal(
    *,
    answer_state: str,
    last_ack_status: str,
    adapter_error: str,
    delivered_waiting_owner: bool,
    timeout_active: bool,
) -> str:
    if _present(adapter_error) or last_ack_status in {"failed", "dead"} or answer_state == "qq_enqueue_failed":
        return "desktop_qq_enqueue_failed"
    if answer_state in RESPONSE_SIGNAL_BY_ANSWER_STATE:
        return RESPONSE_SIGNAL_BY_ANSWER_STATE[answer_state]
    if timeout_active:
        return "owner_no_response_timeout"
    if delivered_waiting_owner:
        return "waiting_owner_response"
    return "none"


def _status_for(*, response_signal: str, delivered_waiting_owner: bool, request_status: str) -> str:
    if response_signal == "desktop_qq_enqueue_failed":
        return "delivery_failed"
    if response_signal == "owner_no_response_timeout":
        return "timeout_active"
    if response_signal in {
        "desktop_read_locally",
        "desktop_dismissed",
        "desktop_owner_replied",
        "desktop_approved_qq",
    }:
        return "response_recorded"
    if delivered_waiting_owner:
        return "waiting"
    if request_status in {"missing", "none", "candidate_only", "ready", "blocked"}:
        return "no_response_expected"
    return "observed"


def _reference_time(request: dict[str, str], dispatch: dict[str, str]) -> str:
    for value in (
        request.get("last_acked_at"),
        dispatch.get("last_acked_at"),
        request.get("updated_at"),
        request.get("created_at"),
        request.get("checked_at"),
        request.get("evaluated_at"),
    ):
        text = _one_line(value, "")
        if text and text.lower() not in NONE_VALUES:
            return text
    return ""


def _minutes_until_timeout(age_minutes: float | None, delivered_waiting_owner: bool) -> str:
    if not delivered_waiting_owner or age_minutes is None:
        return "none"
    return str(max(0, math.ceil(OWNER_NO_RESPONSE_TIMEOUT_MINUTES - age_minutes)))


def _next_timeout_at(reference_time: str, delivered_waiting_owner: bool) -> str:
    if not delivered_waiting_owner:
        return "none"
    parsed = _parse_timestamp(reference_time)
    if parsed is None:
        return "unknown"
    return (parsed + timedelta(minutes=OWNER_NO_RESPONSE_TIMEOUT_MINUTES)).isoformat(timespec="seconds")


def _notes(response_signal: str, delivered_waiting_owner: bool, timeout_active: bool) -> list[str]:
    notes: list[str] = []
    if response_signal != "none":
        notes.append(f"response_signal:{response_signal}")
    if delivered_waiting_owner:
        notes.append("delivered_request_waiting_owner")
    if timeout_active:
        notes.append("owner_no_response_timeout_active")
    if not notes:
        notes.append("no_pending_owner_response_feedback")
    notes.append("raw_text_not_retained")
    return notes


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        if stripped.startswith("- "):
            key, value = stripped[2:].split(":", 1)
        elif re.match(r"^[A-Za-z0-9_]+:\s*", stripped):
            key, value = stripped.split(":", 1)
        else:
            continue
        fields[key.strip()] = value.strip()
    return fields


def _age_minutes(start: Any, end: Any) -> float | None:
    start_dt = _parse_timestamp(start)
    end_dt = _parse_timestamp(end)
    if start_dt is None or end_dt is None:
        return None
    if start_dt.tzinfo is not None and end_dt.tzinfo is not None:
        end_dt = end_dt.astimezone(start_dt.tzinfo)
    elif start_dt.tzinfo is not None and end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=start_dt.tzinfo)
    elif start_dt.tzinfo is None and end_dt.tzinfo is not None:
        start_dt = start_dt.replace(tzinfo=end_dt.tzinfo)
    return max(0.0, (end_dt - start_dt).total_seconds() / 60.0)


def _parse_timestamp(value: Any) -> datetime | None:
    text = _one_line(value, "").replace("Z", "+00:00")
    if not text or text.lower() in NONE_VALUES:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _content_ref(value: Any) -> str:
    text = _one_line(value, "")
    if not text or text.lower() in NONE_VALUES:
        return "none"
    if text.startswith("sha256:"):
        return text[:23]
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _format_minutes(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{value:.1f}"


def _present(value: Any) -> bool:
    return _one_line(value, "").lower() not in NONE_VALUES


def _one_line(value: Any, default: str = "none", *, limit: int = 160) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split()).strip()
    if limit > 0 and len(text) > limit:
        text = text[: max(1, limit - 3)].rstrip() + "..."
    return text if text else default


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose proactive owner response feedback state.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_proactive_response_diagnostics(args.root)
    if args.write:
        report.update(write_proactive_response_diagnostics(args.root, report, output=args.output))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_proactive_response_diagnostics(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
