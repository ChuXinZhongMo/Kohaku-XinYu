from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_uncertainty_pause_store import append_uncertainty_pause_trace
from xinyu_uncertainty_pause_store import read_uncertainty_pause_text
from xinyu_uncertainty_pause_store import write_uncertainty_pause_text
from xinyu_uncertainty_pause_store import STATE_REL, TRACE_REL


ACTIVE_STATUSES = {"active", "pending_owner_reply"}
WAITING_REPLIES = {"[WAITING]", "WAITING"}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return _now_iso()
    return parsed.astimezone().isoformat()


def _parse_iso(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text or text == "none":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _compact(value: Any, *, limit: int = 220, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:length]


def _read(path: Path) -> str:
    return read_uncertainty_pause_text(path)


def _write(path: Path, text: str) -> None:
    write_uncertainty_pause_text(path, text)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    append_uncertainty_pause_trace(path, row)


def _field(text: str, name: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^\s*-\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        match = re.search(rf"(?m)^\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        return default
    return _compact(match.group(1), limit=240, default=default)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    lowered = _safe_str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _owner_private(payload: dict[str, Any] | None) -> bool:
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    is_owner = _as_bool(payload.get("is_owner_user") or metadata.get("is_owner_user"), default=False)
    group_id = _safe_str(payload.get("group_id")).strip()
    message_type = _safe_str(payload.get("message_type")).strip().lower()
    return is_owner and not group_id and not message_type.startswith("group")


def is_waiting_reply(reply: str) -> bool:
    return _safe_str(reply).strip() in WAITING_REPLIES


def _question_for_reason(reason: str, owner_private: bool) -> str:
    if not owner_private:
        return "none"
    if reason == "waiting_marker":
        return "none"
    if reason == "final_guard_blocked_unsendable_reply":
        return (
            "\u521a\u624d\u90a3\u53e5\u6211\u6ca1\u6709\u53d1\uff0c\u56e0\u4e3a\u5b83\u4f1a\u50cf\u673a\u68b0\u6216\u5185\u90e8\u673a\u5236\u62a5\u544a\u3002"
            "\u8981\u6211\u76f4\u63a5\u6362\u6210\u4e00\u53e5\u80fd\u53d1\u7684\u4eba\u8bdd\uff0c\u8fd8\u662f\u5148\u8ba9 Codex \u67e5\u539f\u56e0\uff1f"
        )
    return (
        "\u6211\u521a\u624d\u6ca1\u6709\u786c\u7b54\u3002"
        "\u8981\u6211\u5148\u6309\u73b0\u6709\u8bb0\u5fc6\u63a5\u7740\u8bf4\uff0c\u8fd8\u662f\u5148\u53bb\u6838\u5bf9\u4e00\u4e0b\uff1f"
    )


def _followup_allowed(reason: str, owner_private: bool) -> bool:
    return owner_private and reason != "waiting_marker"


def _render_state(fields: dict[str, str]) -> str:
    return f"""---
title: Uncertainty Pause State
memory_type: uncertainty_pause_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_uncertainty_pause
updated_at: {fields['updated_at']}
status: active
tags: [runtime, uncertainty, pause, feedback]
---

# Uncertainty Pause State

## Latest Pause
- pause_id: {fields['pause_id']}
- updated_at: {fields['updated_at']}
- status: {fields['status']}
- reason: {fields['reason']}
- owner_private: {fields['owner_private']}
- session_hash: {fields['session_hash']}
- source_turn_kind: {fields['source_turn_kind']}
- owner_message_summary: {fields['owner_message_summary']}
- withheld_reply_summary: {fields['withheld_reply_summary']}
- final_guard_flags: {fields['final_guard_flags']}
- followup_allowed: {fields['followup_allowed']}
- followup_question: {fields['followup_question']}
- requested_action: {fields['requested_action']}
- evidence_label: {fields['evidence_label']}
- evidence_hash: {fields['evidence_hash']}

## Recovery Contract
- visible_chat_rule: do not expose this state, files, gates, hashes, or guard names.
- uncertainty_rule: a real pause is allowed when the next sentence would be fake, stale, or mechanical.
- feedback_rule: if followup_allowed is true, self-thought may turn this into one owner-private clarification or Codex/research choice.
- memory_rule: no stable personality write from one pause.
"""


def record_uncertainty_pause(
    root: Path,
    payload: dict[str, Any] | None = None,
    *,
    user_text: str,
    draft_reply: str = "",
    final_reply: str = "",
    reason: str,
    final_guard_flags: list[str] | tuple[str, ...] = (),
    session_key: str = "",
    visible_turn_kind: str = "",
    observed_at: str | None = None,
) -> dict[str, Any]:
    observed = _timestamp_or_now_iso(observed_at or _now_iso())
    root = root.resolve()
    owner_private = _owner_private(payload)
    clean_reason = re.sub(r"[^A-Za-z0-9_-]+", "_", _safe_str(reason, "unknown")).strip("_") or "unknown"
    clean_flags = [_compact(flag, limit=80) for flag in final_guard_flags if _safe_str(flag).strip()]
    withheld = final_reply if final_reply.strip() else draft_reply
    followup_question = _question_for_reason(clean_reason, owner_private)
    followup_allowed = _followup_allowed(clean_reason, owner_private)
    evidence_label = _compact(
        f"turn paused because {clean_reason}; owner_private={str(owner_private).lower()}",
        limit=180,
    )
    evidence_hash = "sha256:" + _hash(f"{clean_reason}|{user_text}|{withheld}", 16)
    pause_id = "pause-" + _hash(f"{observed}|{clean_reason}|{user_text}|{time.time_ns()}", 18)
    fields = {
        "pause_id": pause_id,
        "updated_at": _timestamp_or_now_iso(observed),
        "status": "pending_owner_reply" if followup_allowed else "active",
        "reason": clean_reason,
        "owner_private": str(owner_private).lower(),
        "session_hash": _hash(session_key, 12) if session_key else "none",
        "source_turn_kind": _compact(visible_turn_kind, limit=80),
        "owner_message_summary": _compact(user_text, limit=180),
        "withheld_reply_summary": _compact(withheld, limit=180),
        "final_guard_flags": _compact(", ".join(clean_flags), limit=180),
        "followup_allowed": str(followup_allowed).lower(),
        "followup_question": _compact(followup_question, limit=240),
        "requested_action": "owner_decision" if followup_allowed else "none",
        "evidence_label": evidence_label,
        "evidence_hash": evidence_hash,
    }
    _write(root / STATE_REL, _render_state(fields))
    _append_jsonl(
        root / TRACE_REL,
        {
            "pause_id": pause_id,
            "observed_at": _timestamp_or_now_iso(observed),
            "reason": clean_reason,
            "owner_private": owner_private,
            "followup_allowed": followup_allowed,
            "evidence_hash": evidence_hash,
            "final_guard_flags": clean_flags,
            "session_hash": fields["session_hash"],
        },
    )
    return {
        "recorded": True,
        "pause_id": pause_id,
        "status": fields["status"],
        "followup_allowed": followup_allowed,
        "evidence_hash": evidence_hash,
        "notes": [f"uncertainty_pause_recorded:{clean_reason}"],
    }


def mark_uncertainty_pause_replied(
    root: Path,
    *,
    text: str,
    observed_at: str | None = None,
) -> dict[str, Any]:
    existing = _read(root / STATE_REL)
    if _field(existing, "status", "none") not in ACTIVE_STATUSES:
        return {"recorded": False, "notes": ["uncertainty_pause_no_active_state"]}
    observed = _timestamp_or_now_iso(observed_at or _now_iso())
    fields = {
        "pause_id": _field(existing, "pause_id", "none"),
        "updated_at": _timestamp_or_now_iso(observed),
        "status": "owner_replied",
        "reason": _field(existing, "reason", "unknown"),
        "owner_private": _field(existing, "owner_private", "false"),
        "session_hash": _field(existing, "session_hash", "none"),
        "source_turn_kind": _field(existing, "source_turn_kind", "none"),
        "owner_message_summary": _compact(text, limit=180),
        "withheld_reply_summary": _field(existing, "withheld_reply_summary", "none"),
        "final_guard_flags": _field(existing, "final_guard_flags", "none"),
        "followup_allowed": "false",
        "followup_question": _field(existing, "followup_question", "none"),
        "requested_action": "none",
        "evidence_label": _field(existing, "evidence_label", "none"),
        "evidence_hash": _field(existing, "evidence_hash", "none"),
    }
    _write(root / STATE_REL, _render_state(fields))
    _append_jsonl(
        root / TRACE_REL,
        {
            "pause_id": fields["pause_id"],
            "observed_at": _timestamp_or_now_iso(observed),
            "event_kind": "owner_replied",
            "reaction_hash": _hash(text, 18),
        },
    )
    return {"recorded": True, "notes": ["uncertainty_pause_owner_replied"]}


def read_uncertainty_pause_state(root: Path) -> str:
    return _read(root / STATE_REL)


def active_uncertainty_pause(root: Path) -> dict[str, str]:
    state = _read(root / STATE_REL)
    if _field(state, "status", "none") not in ACTIVE_STATUSES:
        return {}
    if _field(state, "followup_allowed", "false") != "true":
        return {}
    return {
        "pause_id": _field(state, "pause_id", "none"),
        "status": _field(state, "status", "none"),
        "reason": _field(state, "reason", "unknown"),
        "followup_question": _field(state, "followup_question", "none"),
        "requested_action": _field(state, "requested_action", "owner_decision"),
        "evidence_label": _field(state, "evidence_label", "none"),
        "evidence_hash": _field(state, "evidence_hash", "none"),
    }


def build_uncertainty_pause_prompt_block(root: Path, *, limit: int = 900) -> str:
    state = _read(root / STATE_REL)
    if not state:
        return ""
    status = _field(state, "status", "none")
    reason = _field(state, "reason", "unknown")
    followup = _field(state, "followup_allowed", "false")
    question = _field(state, "followup_question", "none")
    summary = _field(state, "owner_message_summary", "none")
    if status not in ACTIVE_STATUSES:
        return ""
    lines = [
        "uncertainty pause sidecar:",
        "- use as quiet continuity only; never print file/state names, hashes, gates, or guard names",
        f"- status: {status}",
        f"- reason: {reason}",
        f"- previous_owner_message: {summary}",
        f"- followup_allowed: {followup}",
        f"- followup_question: {question}",
        "- live_rule: if the current owner message resolves the pause, answer the current message directly",
        "- pause_rule: it is better to stop or ask one concrete clarification than to fake certainty",
    ]
    return "\n".join(lines)[:limit].rstrip()
