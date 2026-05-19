from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_storage_paths import knowledge_file_path


STATE_REL = Path("memory/self/expression_self_learning_state.md")
TRACE_REL = Path("runtime/expression_self_learning_trace.jsonl")
QUESTION_ID = "q-006"
TARGET = "ai-self-understanding"
QUERY = (
    "conversational agents natural dialogue avoiding template responses "
    "tool use transparency human AI interaction reliable source"
)


def _custom_path(root: Path) -> None:
    candidates = [root / "custom", Path(__file__).resolve().parent / "custom"]
    for custom in candidates:
        if custom.exists() and str(custom) not in sys.path:
            sys.path.insert(0, str(custom))


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return _now_iso()
    return parsed.astimezone().isoformat()


def _parse_iso(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text or text.lower() in {"none", "unknown", "null", "n/a", "na"}:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:length]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _compact(value: Any, *, limit: int = 220, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _knowledge(root: Path, filename: str) -> Path:
    return knowledge_file_path(root, filename)


def _next_request_id(existing: list[dict[str, str]], date_part: str) -> str:
    prefix = f"request-{date_part}-expr-"
    numbers: list[int] = []
    for item in existing:
        request_id = item.get("request_id", "")
        if request_id.startswith(prefix):
            try:
                numbers.append(int(request_id.removeprefix(prefix)))
            except ValueError:
                pass
    return f"{prefix}{max(numbers, default=0) + 1:03d}"


def _upsert_source_request(root: Path, *, created_at: str, reason: str) -> tuple[str, bool]:
    _custom_path(root)
    from source_request_planner_engine import render_source_requests, split_requests

    created_at = _timestamp_or_now_iso(created_at)
    path = _knowledge(root, "source_requests.md")
    existing = split_requests(_read(path))
    for item in existing:
        if item.get("question_id") == QUESTION_ID:
            return item.get("request_id", "unknown"), False
    request_id = _next_request_id(existing, created_at[:10])
    existing.append(
        {
            "request_id": request_id,
            "question_id": QUESTION_ID,
            "target": TARGET,
            "query": QUERY,
            "url": "none",
            "status": "pending_url",
            "reason": reason,
            "followup_kind": "self_expression_failure",
            "avoid_host": "none",
            "followup_slot": "1",
        }
    )
    _write(path, render_source_requests(created_at, existing))
    return request_id, True


def _render_state(
    *,
    updated_at: str,
    event_id: str,
    failure_kind: str,
    flags: list[str],
    source_request_id: str,
    source_request_created: bool,
    user_text: str,
    bad_reply: str,
    repaired_reply: str,
) -> str:
    flags_text = ", ".join(flags) if flags else "none"
    return f"""---
title: Expression Self Learning State
memory_type: expression_self_learning_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_expression_self_learning
updated_at: {_timestamp_or_now_iso(updated_at)}
status: active
tags: [self, expression, learning, anti-template]
---

# Expression Self Learning State

## Latest Failure
- event_id: {event_id}
- observed_at: {_timestamp_or_now_iso(updated_at)}
- failure_kind: {failure_kind}
- flags: {_compact(flags_text, limit=180)}
- owner_message_summary: {_compact(user_text, limit=180)}
- blocked_reply_summary: {_compact(bad_reply, limit=180)}
- repaired_reply_summary: {_compact(repaired_reply, limit=180)}

## Learning Request
- question_id: {QUESTION_ID}
- target: {TARGET}
- query: {QUERY}
- source_request_id: {source_request_id}
- source_request_created: {str(source_request_created).lower()}
- search_status: pending_url_or_provider_collection
- learning_goal: understand how conversational agents can avoid template voice, fake tool posture, and visible mechanism leakage.

## Runtime Rule
- visible_reply_policy: do not send pseudo tools, file names, or fixed apology templates to owner-private chat.
- repair_policy: retry the reply as live speech; if retry still leaks mechanism, return an empty visible reply rather than a canned fallback or internal placeholder.
- stable_personality_write: no
"""


def record_expression_self_learning_event(
    root: Path,
    *,
    user_text: str,
    bad_reply: str,
    repaired_reply: str = "",
    flags: list[str] | tuple[str, ...] = (),
    observed_at: str | None = None,
    failure_kind: str = "visible_expression_leak",
) -> dict[str, Any]:
    observed = _timestamp_or_now_iso(observed_at or _now_iso())
    event_id = "expr-learn-" + _hash(f"{observed}|{user_text}|{bad_reply}|{time.time_ns()}", 18)
    clean_flags = [_compact(flag, limit=80) for flag in flags if _safe_str(flag).strip()]
    request_id, created = _upsert_source_request(
        root,
        created_at=observed,
        reason=f"{failure_kind}: XinYu visible reply exposed mechanism or template posture",
    )
    state = _render_state(
        updated_at=_timestamp_or_now_iso(observed),
        event_id=event_id,
        failure_kind=failure_kind,
        flags=clean_flags,
        source_request_id=request_id,
        source_request_created=created,
        user_text=user_text,
        bad_reply=bad_reply,
        repaired_reply=repaired_reply,
    )
    _write(root / STATE_REL, state)
    _append_jsonl(
        root / TRACE_REL,
        {
            "event_id": event_id,
            "observed_at": _timestamp_or_now_iso(observed),
            "failure_kind": failure_kind,
            "flags": clean_flags,
            "source_request_id": request_id,
            "source_request_created": created,
            "bad_reply_hash": _hash(bad_reply, 24),
            "repaired_reply_hash": _hash(repaired_reply, 24),
        },
    )
    return {
        "recorded": True,
        "event_id": event_id,
        "source_request_id": request_id,
        "source_request_created": created,
        "notes": ["expression_self_learning_recorded", f"source_request:{request_id}"],
    }
