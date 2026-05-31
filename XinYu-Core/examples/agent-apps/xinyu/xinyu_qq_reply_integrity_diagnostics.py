from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_state_io import write_text_atomic
from xinyu_visible_text_sanitizer import sanitize_visible_text


ACK_SPOOL_REL = Path("runtime/gateway_ack_spool.jsonl")
ROUTE_TRACE_REL = Path("runtime/turn_route_trace.jsonl")
WORKING_MEMORY_DIR_REL = Path("runtime/dialogue_working_memory")
STATE_REL = Path("memory/context/qq_reply_integrity_diagnostics_state.md")
REPORT_REL = Path("worklog/xinyu-qq-reply-integrity-diagnostics-latest.md")
TRACE_REL = Path("runtime/qq_reply_integrity_diagnostics_trace.jsonl")

DEFAULT_ACK_LIMIT = 500
DEFAULT_ROUTE_TRACE_LIMIT = 1200
DEFAULT_LOOKBACK_MINUTES = 120

NAKED_ACK_TEXTS = {
    "\u55ef",
    "\u55ef.",
    "\u55ef\u3002",
    "\u55ef!",
    "\u55ef\uff01",
    "\u55ef?",
    "\u55ef\uff1f",
    "\u55ef\u55ef",
    "\u55ef\u55ef.",
    "\u55ef\u55ef\u3002",
}


def build_qq_reply_integrity_diagnostics(
    root: Path,
    *,
    ack_limit: int = DEFAULT_ACK_LIMIT,
    route_trace_limit: int = DEFAULT_ROUTE_TRACE_LIMIT,
    lookback_minutes: int = DEFAULT_LOOKBACK_MINUTES,
    since: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    generated_at = generated_at or _now_iso()
    now = _parse_timestamp(generated_at)
    since_time = _parse_timestamp(since)

    route_rows = _read_jsonl_tail(root / ROUTE_TRACE_REL, max_lines=max(1, int(route_trace_limit)))
    direct_events = _semantic_fast_direct_events(
        route_rows,
        now=now,
        lookback_minutes=max(0, int(lookback_minutes)),
        since=since_time,
    )
    direct_turns = {event["turn_id"]: event for event in direct_events if event.get("turn_id")}

    ack_rows = _read_jsonl_tail(root / ACK_SPOOL_REL, max_lines=max(1, int(ack_limit)))
    replies = _visible_chat_replies(
        ack_rows,
        now=now,
        lookback_minutes=max(0, int(lookback_minutes)),
        since=since_time,
    )
    working_memory = _working_memory_index(root)

    issues: list[dict[str, Any]] = []
    visible_with_working_memory = 0
    visible_without_working_memory = 0
    naked_ack_count = 0
    semantic_direct_without_archive = 0

    for reply in replies:
        turn_id = _safe_str(reply.get("turn_id"))
        reply_hash = _safe_str(reply.get("visible_text_hash"))
        in_working_memory = _reply_in_working_memory(reply, working_memory)
        reply["working_memory_status"] = "present" if in_working_memory else "missing"
        if in_working_memory:
            visible_with_working_memory += 1
        else:
            visible_without_working_memory += 1
            issues.append(_issue("visible_reply_missing_working_memory", reply))

        if bool(reply.get("naked_ack")):
            naked_ack_count += 1
            issues.append(_issue("naked_ack_visible_reply", reply))

        if turn_id in direct_turns:
            reply["semantic_fast_direct_reply"] = True
            if reply.get("archive_status") != "present":
                semantic_direct_without_archive += 1
                issues.append(_issue("semantic_fast_direct_reply_without_archive", reply))
        else:
            reply["semantic_fast_direct_reply"] = False

        if not reply_hash:
            reply["visible_text_hash"] = _content_hash(reply.get("visible_text", ""))

    matched_turns = {str(reply.get("turn_id") or "") for reply in replies if str(reply.get("turn_id") or "")}
    semantic_direct_without_visible_ack = 0
    for event in direct_events:
        turn_id = str(event.get("turn_id") or "")
        if turn_id and turn_id not in matched_turns:
            semantic_direct_without_visible_ack += 1
            issues.append(
                {
                    "issue_type": "semantic_fast_direct_reply_without_visible_ack",
                    "turn_id": turn_id,
                    "created_at": event.get("observed_at", ""),
                    "reply_ref": "none",
                    "route": "owner_private_semantic_fast",
                    "archive_status": "unknown",
                    "working_memory_status": "unknown",
                }
            )

    status = _status(
        visible_reply_count=len(replies),
        issue_count=len(issues),
        semantic_fast_direct_reply_count=len(direct_events),
    )
    latest_reply = _latest_reply_summary(replies[-1] if replies else {})
    report = {
        "ok": status in {"pass", "no_samples"},
        "status": status,
        "generated_at": generated_at,
        "root": str(root),
        "ack_limit": max(1, int(ack_limit)),
        "route_trace_limit": max(1, int(route_trace_limit)),
        "lookback_minutes": max(0, int(lookback_minutes)),
        "since": since or "",
        "metrics": {
            "visible_chat_reply_count": len(replies),
            "visible_reply_with_working_memory_count": visible_with_working_memory,
            "visible_reply_missing_working_memory_count": visible_without_working_memory,
            "naked_ack_visible_reply_count": naked_ack_count,
            "semantic_fast_direct_reply_count": len(direct_events),
            "semantic_fast_direct_reply_without_archive_count": semantic_direct_without_archive,
            "semantic_fast_direct_reply_without_visible_ack_count": semantic_direct_without_visible_ack,
            "working_memory_file_count": working_memory["file_count"],
            "working_memory_row_count": working_memory["row_count"],
            "working_memory_assistant_hash_count": len(working_memory["assistant_hashes"]),
            "issue_count": len(issues),
        },
        "latest_visible_reply": latest_reply,
        "issues": issues[-50:],
        "privacy": {
            "raw_owner_text_in_report": False,
            "visible_reply_text_in_report": False,
            "state_contains_hashes_counts_only": True,
            "stable_memory_write": "blocked",
        },
        "notes": _notes(status, len(replies), len(direct_events), issues),
    }
    return report


def render_qq_reply_integrity_diagnostics(report: dict[str, Any]) -> str:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    latest = report.get("latest_visible_reply") if isinstance(report.get("latest_visible_reply"), dict) else {}
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    lines = [
        "# XinYu QQ Reply Integrity Diagnostics",
        "",
        f"- generated_at: {report.get('generated_at', 'unknown')}",
        f"- status: {report.get('status', 'unknown')}",
        f"- result: {'pass' if report.get('ok') else 'needs_check'}",
        f"- lookback_minutes: {report.get('lookback_minutes', 'unknown')}",
        f"- since: {report.get('since', '') or 'none'}",
        "- claim_boundary: QQ reply transport and short-term persistence only; no consciousness claim",
        "",
        "## Metrics",
    ]
    for key in (
        "visible_chat_reply_count",
        "visible_reply_with_working_memory_count",
        "visible_reply_missing_working_memory_count",
        "naked_ack_visible_reply_count",
        "semantic_fast_direct_reply_count",
        "semantic_fast_direct_reply_without_archive_count",
        "semantic_fast_direct_reply_without_visible_ack_count",
        "working_memory_file_count",
        "working_memory_row_count",
        "working_memory_assistant_hash_count",
        "issue_count",
    ):
        lines.append(f"- {key}: {metrics.get(key, 'missing')}")
    lines.extend(["", "## Latest Visible Reply"])
    for key in (
        "created_at",
        "turn_id",
        "reply_ref",
        "archive_status",
        "working_memory_status",
        "semantic_fast_direct_reply",
        "naked_ack",
    ):
        lines.append(f"- {key}: {latest.get(key, 'missing')}")
    lines.extend(["", "## Issues"])
    issues = report.get("issues") if isinstance(report.get("issues"), list) else []
    if issues:
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            lines.append(
                "- "
                f"{issue.get('issue_type', 'unknown')} "
                f"turn_id={issue.get('turn_id', 'none')} "
                f"reply_ref={issue.get('reply_ref', 'none')} "
                f"archive={issue.get('archive_status', 'unknown')} "
                f"working_memory={issue.get('working_memory_status', 'unknown')}"
            )
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


def write_qq_reply_integrity_diagnostics(
    root: Path,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> dict[str, str]:
    root = root.resolve()
    report_path = output if output is not None else root / REPORT_REL
    if not report_path.is_absolute():
        report_path = root / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_qq_reply_integrity_diagnostics(report), encoding="utf-8")
    _write_state(root, report, report_path=report_path)
    _append_trace(root, report)
    return {"report_path": str(report_path), "state_path": str(root / STATE_REL)}


def _write_state(root: Path, report: dict[str, Any], *, report_path: Path) -> None:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    latest = report.get("latest_visible_reply") if isinstance(report.get("latest_visible_reply"), dict) else {}
    text = f"""---
title: QQ Reply Integrity Diagnostics State
memory_type: qq_reply_integrity_diagnostics_state
time_scope: rolling_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_qq_reply_integrity_diagnostics
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [qq, continuity, diagnostics, working-memory, semantic-fast]
---

# QQ Reply Integrity Diagnostics State

## Current Window
- status: {report.get('status', 'unknown')}
- checked_at: {report.get('generated_at', 'unknown')}
- lookback_minutes: {report.get('lookback_minutes', 'unknown')}
- visible_chat_reply_count: {metrics.get('visible_chat_reply_count', 0)}
- visible_reply_with_working_memory_count: {metrics.get('visible_reply_with_working_memory_count', 0)}
- visible_reply_missing_working_memory_count: {metrics.get('visible_reply_missing_working_memory_count', 0)}
- naked_ack_visible_reply_count: {metrics.get('naked_ack_visible_reply_count', 0)}
- semantic_fast_direct_reply_count: {metrics.get('semantic_fast_direct_reply_count', 0)}
- semantic_fast_direct_reply_without_archive_count: {metrics.get('semantic_fast_direct_reply_without_archive_count', 0)}
- semantic_fast_direct_reply_without_visible_ack_count: {metrics.get('semantic_fast_direct_reply_without_visible_ack_count', 0)}
- issue_count: {metrics.get('issue_count', 0)}

## Latest Visible Reply
- latest_created_at: {latest.get('created_at', 'none')}
- latest_turn_id: {latest.get('turn_id', 'none')}
- latest_reply_ref: {latest.get('reply_ref', 'none')}
- latest_archive_status: {latest.get('archive_status', 'missing')}
- latest_working_memory_status: {latest.get('working_memory_status', 'missing')}
- latest_semantic_fast_direct_reply: {str(latest.get('semantic_fast_direct_reply', False)).lower()}
- latest_naked_ack: {str(latest.get('naked_ack', False)).lower()}

## Boundaries
- report_path: {report_path.as_posix()}
- raw_owner_text_in_state: false
- visible_reply_text_in_state: false
- stable_memory_write: blocked
"""
    write_text_atomic(root / STATE_REL, text)


def _append_trace(root: Path, report: dict[str, Any]) -> None:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    row = {
        "generated_at": report.get("generated_at", ""),
        "status": report.get("status", ""),
        "ok": bool(report.get("ok")),
        "visible_chat_reply_count": metrics.get("visible_chat_reply_count", 0),
        "visible_reply_missing_working_memory_count": metrics.get(
            "visible_reply_missing_working_memory_count",
            0,
        ),
        "naked_ack_visible_reply_count": metrics.get("naked_ack_visible_reply_count", 0),
        "semantic_fast_direct_reply_count": metrics.get("semantic_fast_direct_reply_count", 0),
        "semantic_fast_direct_reply_without_archive_count": metrics.get(
            "semantic_fast_direct_reply_without_archive_count",
            0,
        ),
        "semantic_fast_direct_reply_without_visible_ack_count": metrics.get(
            "semantic_fast_direct_reply_without_visible_ack_count",
            0,
        ),
        "raw_owner_text_in_trace": False,
        "visible_reply_text_in_trace": False,
    }
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def _semantic_fast_direct_events(
    rows: list[dict[str, Any]],
    *,
    now: datetime | None,
    lookback_minutes: int,
    since: datetime | None,
) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    for row in rows:
        notes = row.get("notes")
        if not isinstance(notes, list):
            notes = []
        if row.get("stage") != "route_finished":
            continue
        if row.get("route") != "owner_private_semantic_fast":
            continue
        if "semantic_fast_direct_reply" not in {str(note) for note in notes}:
            continue
        observed_at = _safe_str(row.get("observed_at"))
        if not _timestamp_in_window(observed_at, now=now, lookback_minutes=lookback_minutes, since=since):
            continue
        events.append(
            {
                "observed_at": observed_at,
                "turn_id": _safe_str(row.get("turn_id")),
                "status": _safe_str(row.get("status")),
            }
        )
    return events


def _visible_chat_replies(
    rows: list[dict[str, Any]],
    *,
    now: datetime | None,
    lookback_minutes: int,
    since: datetime | None,
) -> list[dict[str, Any]]:
    replies: list[dict[str, Any]] = []
    for row in rows:
        if row.get("event") != "pending":
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        route = _safe_str(payload.get("route") or row.get("route"))
        if route != "chat":
            continue
        visible_text = _safe_str(payload.get("visible_text")).strip()
        if not visible_text:
            continue
        created_at = _safe_str(payload.get("sent_at") or row.get("created_at"))
        if not _timestamp_in_window(created_at, now=now, lookback_minutes=lookback_minutes, since=since):
            continue
        reply_hash = _safe_str(payload.get("visible_text_hash")) or _content_hash(visible_text)
        archive_ids = payload.get("archive_message_ids")
        archive_assistant_id = _safe_str(payload.get("archive_assistant_message_id"))
        archive_present = (
            isinstance(archive_ids, list)
            and len(archive_ids) > 0
        ) or bool(archive_assistant_id)
        replies.append(
            {
                "created_at": created_at,
                "turn_id": _safe_str(payload.get("turn_id")),
                "route": route,
                "visible_text": visible_text,
                "visible_text_hash": reply_hash,
                "reply_ref": _short_hash(reply_hash or _content_hash(visible_text)),
                "archive_status": "present" if archive_present else "missing",
                "archive_message_count": len(archive_ids) if isinstance(archive_ids, list) else 0,
                "naked_ack": _is_naked_ack(visible_text),
            }
        )
    return replies


def _working_memory_index(root: Path) -> dict[str, Any]:
    working_dir = root / WORKING_MEMORY_DIR_REL
    files = list(working_dir.glob("*.jsonl")) if working_dir.exists() else []
    assistant_hashes: set[str] = set()
    assistant_texts: set[str] = set()
    row_count = 0
    assistant_row_count = 0
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue
            row_count += 1
            if _safe_str(data.get("role")) != "assistant":
                continue
            content = _safe_str(data.get("content")).strip()
            if not content:
                continue
            assistant_row_count += 1
            assistant_hashes.add(_content_hash(content))
            assistant_texts.add(_normalize_content(sanitize_visible_text(content)))
    return {
        "file_count": len(files),
        "row_count": row_count,
        "assistant_row_count": assistant_row_count,
        "assistant_hashes": assistant_hashes,
        "assistant_texts": assistant_texts,
    }


def _reply_in_working_memory(reply: dict[str, Any], working_memory: dict[str, Any]) -> bool:
    reply_hash = _safe_str(reply.get("visible_text_hash")) or _content_hash(reply.get("visible_text", ""))
    if reply_hash and reply_hash in working_memory.get("assistant_hashes", set()):
        return True
    visible_text = _normalize_content(sanitize_visible_text(_safe_str(reply.get("visible_text"))))
    return bool(visible_text and visible_text in working_memory.get("assistant_texts", set()))


def _issue(issue_type: str, reply: dict[str, Any]) -> dict[str, Any]:
    return {
        "issue_type": issue_type,
        "turn_id": _safe_str(reply.get("turn_id")) or "none",
        "created_at": _safe_str(reply.get("created_at")),
        "reply_ref": _safe_str(reply.get("reply_ref")) or _short_hash(_safe_str(reply.get("visible_text_hash"))),
        "route": _safe_str(reply.get("route")) or "chat",
        "archive_status": _safe_str(reply.get("archive_status")) or "unknown",
        "working_memory_status": _safe_str(reply.get("working_memory_status")) or "unknown",
    }


def _latest_reply_summary(reply: dict[str, Any]) -> dict[str, Any]:
    if not reply:
        return {
            "created_at": "none",
            "turn_id": "none",
            "reply_ref": "none",
            "archive_status": "none",
            "working_memory_status": "none",
            "semantic_fast_direct_reply": False,
            "naked_ack": False,
        }
    return {
        "created_at": _safe_str(reply.get("created_at")) or "none",
        "turn_id": _safe_str(reply.get("turn_id")) or "none",
        "reply_ref": _safe_str(reply.get("reply_ref")) or _short_hash(_safe_str(reply.get("visible_text_hash"))),
        "archive_status": _safe_str(reply.get("archive_status")) or "unknown",
        "working_memory_status": _safe_str(reply.get("working_memory_status")) or "unknown",
        "semantic_fast_direct_reply": bool(reply.get("semantic_fast_direct_reply")),
        "naked_ack": bool(reply.get("naked_ack")),
    }


def _status(*, visible_reply_count: int, issue_count: int, semantic_fast_direct_reply_count: int) -> str:
    if visible_reply_count <= 0 and semantic_fast_direct_reply_count <= 0:
        return "no_samples"
    if issue_count:
        return "needs_check"
    return "pass"


def _notes(
    status: str,
    visible_reply_count: int,
    semantic_fast_direct_reply_count: int,
    issues: list[dict[str, Any]],
) -> list[str]:
    notes: list[str] = []
    if visible_reply_count <= 0 and semantic_fast_direct_reply_count <= 0:
        notes.append("no_recent_visible_chat_replies_or_semantic_fast_direct_samples")
    if any(issue.get("issue_type") == "naked_ack_visible_reply" for issue in issues):
        notes.append("naked_ack_visible_reply_observed")
    if any(issue.get("issue_type") == "semantic_fast_direct_reply_without_archive" for issue in issues):
        notes.append("semantic_fast_direct_reply_without_archive_observed")
    if any(issue.get("issue_type") == "visible_reply_missing_working_memory" for issue in issues):
        notes.append("visible_reply_missing_working_memory_observed")
    if status == "pass":
        notes.append("recent_visible_replies_have_working_memory_and_no_naked_ack_or_bad_fast_direct")
    return notes


def _timestamp_in_window(
    value: Any,
    *,
    now: datetime | None,
    lookback_minutes: int,
    since: datetime | None,
) -> bool:
    timestamp = _parse_timestamp(value)
    if timestamp is None:
        return True
    if since is not None and not _timestamp_not_before(timestamp, since):
        return False
    if since is not None or lookback_minutes <= 0 or now is None:
        return True
    seconds = _seconds_between(now, timestamp)
    return 0 <= seconds <= lookback_minutes * 60


def _timestamp_not_before(left: datetime, right: datetime) -> bool:
    compare_left = left
    compare_right = right
    if left.tzinfo is not None and right.tzinfo is not None:
        compare_right = right.astimezone(left.tzinfo)
    elif left.tzinfo is not None and right.tzinfo is None:
        compare_right = right.replace(tzinfo=left.tzinfo)
    elif left.tzinfo is None and right.tzinfo is not None:
        compare_left = left.replace(tzinfo=right.tzinfo)
    return compare_left >= compare_right


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


def _content_hash(value: Any) -> str:
    text = _normalize_content(sanitize_visible_text(value))
    if not text:
        return ""
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _short_hash(value: Any) -> str:
    text = _safe_str(value).strip()
    if text.startswith("sha256:"):
        return "sha256:" + text.split("sha256:", 1)[1][:16]
    if not text:
        return "none"
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _normalize_content(value: Any) -> str:
    return re.sub(r"\s+", " ", _safe_str(value)).strip()


def _is_naked_ack(value: Any) -> bool:
    text = re.sub(r"\s+", "", _safe_str(value))
    return text in NAKED_ACK_TEXTS


def _read_jsonl_tail(path: Path, *, max_lines: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-max(1, int(max_lines)) :]:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _parse_timestamp(value: Any) -> datetime | None:
    text = _safe_str(value).strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build XinYu QQ reply integrity diagnostics.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--ack-limit", type=int, default=DEFAULT_ACK_LIMIT)
    parser.add_argument("--route-trace-limit", type=int, default=DEFAULT_ROUTE_TRACE_LIMIT)
    parser.add_argument("--lookback-minutes", type=int, default=DEFAULT_LOOKBACK_MINUTES)
    parser.add_argument("--since", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_qq_reply_integrity_diagnostics(
        args.root,
        ack_limit=max(1, args.ack_limit),
        route_trace_limit=max(1, args.route_trace_limit),
        lookback_minutes=max(0, args.lookback_minutes),
        since=args.since,
    )
    if args.write:
        report.update(write_qq_reply_integrity_diagnostics(args.root, report, output=args.output))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_qq_reply_integrity_diagnostics(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
