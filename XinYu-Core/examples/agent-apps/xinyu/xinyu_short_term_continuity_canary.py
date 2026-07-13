from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_short_term_continuity_canary_store import STATE_REL
from xinyu_short_term_continuity_canary_store import append_short_term_continuity_canary_trace_event
from xinyu_short_term_continuity_canary_store import read_gateway_ack_spool_jsonl_tail
from xinyu_short_term_continuity_canary_store import read_short_term_continuity_jsonl_tail
from xinyu_short_term_continuity_canary_store import write_short_term_continuity_canary_report_text
from xinyu_short_term_continuity_canary_store import write_short_term_continuity_canary_state_text

WHICH_SENTENCE_MARKERS = (
    "哪一句",
    "哪几句",
    "哪两句",
    "哪句",
    "哪一段",
    "哪几段",
    "哪两段",
)


def build_short_term_continuity_canary_report(
    root: Path,
    *,
    trace_limit: int = 200,
    ack_limit: int = 800,
    reply_window_seconds: int = 240,
    lookback_minutes: int | None = None,
    since: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    generated_at = generated_at or _now_iso()
    now = _parse_timestamp(generated_at)
    since_time = _parse_timestamp(since)
    trace_rows = read_short_term_continuity_jsonl_tail(root, max_lines=max(1, int(trace_limit)))
    ack_rows = read_gateway_ack_spool_jsonl_tail(root, max_lines=max(1, int(ack_limit)))
    replies = _reply_records(ack_rows)
    direct_events = [
        _safe_continuity_event(row)
        for row in trace_rows
        if row.get("direct_reference") is True
        and _timestamp_in_window(
            row.get("checked_at"),
            now=now,
            lookback_minutes=lookback_minutes,
            since=since_time,
        )
    ]

    matched: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    recurrence_refs: list[str] = []
    for event in direct_events:
        reply = _match_reply(event, replies, window_seconds=max(1, int(reply_window_seconds)))
        if reply is None:
            unmatched.append(event)
            continue
        asked = _reply_asks_which_sentence(reply.get("visible_text", ""))
        item = {
            "checked_at": event.get("checked_at", ""),
            "turn_id": event.get("turn_id", ""),
            "recall_status": event.get("recall_status", ""),
            "recall_source": event.get("recall_source", ""),
            "reply_ref": reply.get("visible_text_hash") or _content_ref(reply.get("visible_text", "")),
            "reply_asked_which_sentence": asked,
            "match_method": reply.get("match_method", ""),
        }
        matched.append(item)
        if asked:
            recurrence_refs.append(str(item["reply_ref"]))

    direct_count = len(direct_events)
    recall_available = sum(1 for item in direct_events if item.get("recall_status") == "tail_available")
    recall_missing = sum(1 for item in direct_events if item.get("recall_status") == "tail_missing")
    tail_source = sum(1 for item in direct_events if item.get("recall_source") == "dialogue_tail")
    archive_source = sum(1 for item in direct_events if item.get("recall_source") == "dialogue_archive")
    none_source = sum(1 for item in direct_events if item.get("recall_source") in {"none", "", "missing"})
    raw_private_retained = sum(1 for item in direct_events if item.get("raw_private_body_retained") is True)
    visible_reply_retained = sum(1 for item in direct_events if item.get("visible_reply_text_retained") is True)
    recurrence_count = len(recurrence_refs)
    matched_count = len(matched)
    unmatched_count = len(unmatched)

    if direct_count == 0:
        status = "no_samples"
    elif recall_missing or recurrence_count or raw_private_retained or visible_reply_retained:
        status = "needs_check"
    elif unmatched_count:
        status = "partial"
    else:
        status = "pass"

    latest = direct_events[-1] if direct_events else {}
    report = {
        "ok": status in {"pass", "no_samples"},
        "status": status,
        "generated_at": generated_at,
        "root": str(root),
        "trace_limit": max(1, int(trace_limit)),
        "ack_limit": max(1, int(ack_limit)),
        "reply_window_seconds": max(1, int(reply_window_seconds)),
        "lookback_minutes": lookback_minutes,
        "since": since or "",
        "metrics": {
            "direct_reference_count": direct_count,
            "recall_available_count": recall_available,
            "recall_missing_count": recall_missing,
            "recall_source_dialogue_tail_count": tail_source,
            "recall_source_dialogue_archive_count": archive_source,
            "recall_source_none_count": none_source,
            "matched_reply_count": matched_count,
            "unmatched_reply_count": unmatched_count,
            "which_sentence_recurrence_count": recurrence_count,
            "direct_reference_recall_success_rate_pct": _pct(recall_available, direct_count),
            "which_sentence_recurrence_rate_pct": _pct(recurrence_count, matched_count),
            "raw_private_body_retained_count": raw_private_retained,
            "visible_reply_text_retained_count": visible_reply_retained,
        },
        "latest_direct_reference": {
            "checked_at": latest.get("checked_at", "none"),
            "turn_id": latest.get("turn_id", "none"),
            "recall_status": latest.get("recall_status", "none"),
            "recall_source": latest.get("recall_source", "none"),
            "latest_user_ref": latest.get("latest_user_ref", "none"),
            "latest_assistant_ref": latest.get("latest_assistant_ref", "none"),
        },
        "matched_direct_references": matched[-20:],
        "unmatched_direct_reference_count": unmatched_count,
        "which_sentence_recurrence_refs": recurrence_refs[-20:],
        "privacy": {
            "raw_owner_text_in_report": False,
            "visible_reply_text_in_report": False,
            "state_contains_hashes_counts_only": True,
            "stable_memory_write": "blocked",
        },
        "notes": _notes(status, direct_count, recall_missing, recurrence_count, unmatched_count),
    }
    return report


def render_short_term_continuity_canary_report(report: dict[str, Any]) -> str:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    latest = report.get("latest_direct_reference") if isinstance(report.get("latest_direct_reference"), dict) else {}
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    lines = [
        "# XinYu Short-Term Continuity Canary",
        "",
        f"- generated_at: {report.get('generated_at', 'unknown')}",
        f"- status: {report.get('status', 'unknown')}",
        f"- result: {'pass' if report.get('ok') else 'needs_check'}",
        f"- lookback_minutes: {report.get('lookback_minutes', '') or 'none'}",
        f"- since: {report.get('since', '') or 'none'}",
        "- claim_boundary: continuity metrics only; does not claim consciousness",
        "",
        "## Metrics",
    ]
    for key in (
        "direct_reference_count",
        "recall_available_count",
        "recall_missing_count",
        "direct_reference_recall_success_rate_pct",
        "recall_source_dialogue_tail_count",
        "recall_source_dialogue_archive_count",
        "recall_source_none_count",
        "matched_reply_count",
        "unmatched_reply_count",
        "which_sentence_recurrence_count",
        "which_sentence_recurrence_rate_pct",
        "raw_private_body_retained_count",
        "visible_reply_text_retained_count",
    ):
        lines.append(f"- {key}: {metrics.get(key, 'missing')}")
    lines.extend(["", "## Latest Direct Reference"])
    for key in (
        "checked_at",
        "turn_id",
        "recall_status",
        "recall_source",
        "latest_user_ref",
        "latest_assistant_ref",
    ):
        lines.append(f"- {key}: {latest.get(key, 'missing')}")
    lines.extend(["", "## Recurrence Refs"])
    refs = report.get("which_sentence_recurrence_refs")
    if isinstance(refs, list) and refs:
        lines.extend(f"- {ref}" for ref in refs)
    else:
        lines.append("- none")
    lines.extend(["", "## Privacy Boundary"])
    for key, value in privacy.items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Notes"])
    notes = report.get("notes") if isinstance(report.get("notes"), list) else []
    if notes:
        lines.extend(f"- {note}" for note in notes)
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def write_short_term_continuity_canary(
    root: Path,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> dict[str, str]:
    root = root.resolve()
    report_path = write_short_term_continuity_canary_report_text(
        root,
        render_short_term_continuity_canary_report(report),
        output=output,
    )
    _write_state(root, report, report_path=report_path)
    _append_trace(root, report)
    return {"report_path": str(report_path), "state_path": str(root / STATE_REL)}


def _write_state(root: Path, report: dict[str, Any], *, report_path: Path) -> None:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    latest = report.get("latest_direct_reference") if isinstance(report.get("latest_direct_reference"), dict) else {}
    text = f"""---
title: Short Term Continuity Canary State
memory_type: short_term_continuity_canary_state
time_scope: rolling_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_short_term_continuity_canary
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [continuity, canary, recall, metrics]
---

# Short Term Continuity Canary State

## Current Window
- status: {report.get('status', 'unknown')}
- checked_at: {report.get('generated_at', 'unknown')}
- direct_reference_count: {metrics.get('direct_reference_count', 0)}
- recall_available_count: {metrics.get('recall_available_count', 0)}
- recall_missing_count: {metrics.get('recall_missing_count', 0)}
- direct_reference_recall_success_rate_pct: {metrics.get('direct_reference_recall_success_rate_pct', 0.0)}
- recall_source_dialogue_tail_count: {metrics.get('recall_source_dialogue_tail_count', 0)}
- recall_source_dialogue_archive_count: {metrics.get('recall_source_dialogue_archive_count', 0)}
- matched_reply_count: {metrics.get('matched_reply_count', 0)}
- unmatched_reply_count: {metrics.get('unmatched_reply_count', 0)}
- which_sentence_recurrence_count: {metrics.get('which_sentence_recurrence_count', 0)}
- which_sentence_recurrence_rate_pct: {metrics.get('which_sentence_recurrence_rate_pct', 0.0)}
- raw_private_body_retained_count: {metrics.get('raw_private_body_retained_count', 0)}
- visible_reply_text_retained_count: {metrics.get('visible_reply_text_retained_count', 0)}

## Latest Direct Reference
- latest_checked_at: {latest.get('checked_at', 'none')}
- latest_turn_id: {latest.get('turn_id', 'none')}
- latest_recall_status: {latest.get('recall_status', 'none')}
- latest_recall_source: {latest.get('recall_source', 'none')}
- latest_user_ref: {latest.get('latest_user_ref', 'none')}
- latest_assistant_ref: {latest.get('latest_assistant_ref', 'none')}

## Boundaries
- report_path: {report_path.as_posix()}
- raw_owner_text_in_state: false
- visible_reply_text_in_state: false
- stable_memory_write: blocked
"""
    write_short_term_continuity_canary_state_text(root, text)


def _append_trace(root: Path, report: dict[str, Any]) -> None:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    row = {
        "generated_at": report.get("generated_at", ""),
        "status": report.get("status", ""),
        "ok": bool(report.get("ok")),
        "direct_reference_count": metrics.get("direct_reference_count", 0),
        "recall_available_count": metrics.get("recall_available_count", 0),
        "recall_missing_count": metrics.get("recall_missing_count", 0),
        "matched_reply_count": metrics.get("matched_reply_count", 0),
        "which_sentence_recurrence_count": metrics.get("which_sentence_recurrence_count", 0),
        "raw_owner_text_in_trace": False,
        "visible_reply_text_in_trace": False,
    }
    append_short_term_continuity_canary_trace_event(root, row)


def _reply_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        if row.get("event") != "pending":
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        route = str(payload.get("route") or row.get("route") or "")
        if route != "chat":
            continue
        result.append(
            {
                "created_at": payload.get("sent_at") or row.get("created_at") or "",
                "turn_id": str(payload.get("turn_id") or ""),
                "source_message_id": str(payload.get("source_message_id") or ""),
                "visible_text": str(payload.get("visible_text") or ""),
                "visible_text_hash": str(payload.get("visible_text_hash") or ""),
                "route": route,
            }
        )
    return result


def _match_reply(event: dict[str, Any], replies: list[dict[str, Any]], *, window_seconds: int) -> dict[str, Any] | None:
    turn_id = str(event.get("turn_id") or "").strip()
    if turn_id and turn_id != "none":
        for reply in reversed(replies):
            if str(reply.get("turn_id") or "") == turn_id:
                matched = dict(reply)
                matched["match_method"] = "turn_id"
                return matched
    event_time = _parse_timestamp(event.get("checked_at"))
    if event_time is None:
        return None
    candidates: list[tuple[float, dict[str, Any]]] = []
    for reply in replies:
        reply_time = _parse_timestamp(reply.get("created_at"))
        if reply_time is None:
            continue
        seconds = _seconds_between(reply_time, event_time)
        if 0 <= seconds <= window_seconds:
            candidates.append((seconds, reply))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    matched = dict(candidates[0][1])
    matched["match_method"] = "time_window"
    return matched


def _safe_continuity_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "checked_at": str(row.get("checked_at") or ""),
        "turn_id": str(row.get("turn_id") or ""),
        "status": str(row.get("status") or ""),
        "direct_reference": bool(row.get("direct_reference")),
        "recall_status": str(row.get("recall_status") or ""),
        "recall_source": str(row.get("recall_source") or ""),
        "tail_count": _as_int(row.get("tail_count")),
        "archive_recovered_count": _as_int(row.get("archive_recovered_count")),
        "recent_user_count": _as_int(row.get("recent_user_count")),
        "recent_assistant_count": _as_int(row.get("recent_assistant_count")),
        "latest_user_ref": str(row.get("latest_user_ref") or "none"),
        "latest_assistant_ref": str(row.get("latest_assistant_ref") or "none"),
        "raw_private_body_retained": row.get("raw_private_body_retained") is True,
        "visible_reply_text_retained": row.get("visible_reply_text_retained") is True,
    }


def _reply_asks_which_sentence(text: Any) -> bool:
    clean = str(text or "")
    return any(marker in clean for marker in WHICH_SENTENCE_MARKERS)


def _content_ref(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "none"
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((part / total) * 100.0, 2)


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _seconds_between(left: datetime, right: datetime) -> float:
    compare_left = left
    compare_right = right
    if left.tzinfo is not None and right.tzinfo is not None:
        compare_right = right.astimezone(left.tzinfo)
    elif left.tzinfo is not None and right.tzinfo is None:
        compare_right = right.replace(tzinfo=left.tzinfo)
    elif left.tzinfo is None and right.tzinfo is not None:
        compare_left = left.replace(tzinfo=right.tzinfo)
    return (compare_left - compare_right).total_seconds()


def _timestamp_in_window(
    value: Any,
    *,
    now: datetime | None,
    lookback_minutes: int | None,
    since: datetime | None,
) -> bool:
    timestamp = _parse_timestamp(value)
    if timestamp is None:
        return True
    if since is not None and _seconds_between(timestamp, since) < 0:
        return False
    if since is not None or lookback_minutes is None or int(lookback_minutes) <= 0 or now is None:
        return True
    seconds = _seconds_between(now, timestamp)
    return 0 <= seconds <= int(lookback_minutes) * 60


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _notes(
    status: str,
    direct_count: int,
    recall_missing: int,
    recurrence_count: int,
    unmatched_count: int,
) -> list[str]:
    notes: list[str] = []
    if direct_count == 0:
        notes.append("no_direct_reference_samples_in_window")
    if recall_missing:
        notes.append("direct_reference_recall_missing_observed")
    if recurrence_count:
        notes.append("which_sentence_recurrence_observed")
    if unmatched_count:
        notes.append("some_direct_reference_events_have_no_matched_reply")
    if status == "pass":
        notes.append("direct_reference_samples_recalled_without_which_sentence_recurrence")
    return notes


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build XinYu short-term continuity canary metrics.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--trace-limit", type=int, default=200)
    parser.add_argument("--ack-limit", type=int, default=800)
    parser.add_argument("--reply-window-seconds", type=int, default=240)
    parser.add_argument("--lookback-minutes", type=int, default=None)
    parser.add_argument("--since", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_short_term_continuity_canary_report(
        args.root,
        trace_limit=max(1, args.trace_limit),
        ack_limit=max(1, args.ack_limit),
        reply_window_seconds=max(1, args.reply_window_seconds),
        lookback_minutes=args.lookback_minutes,
        since=args.since,
    )
    if args.write:
        report.update(write_short_term_continuity_canary(args.root, report, output=args.output))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_short_term_continuity_canary_report(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
