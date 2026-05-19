from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any


STATE_REL = Path("memory/context/continuity_handoff_state.md")
TRACE_REL = Path("runtime/continuity_handoff_trace.jsonl")
REPAIR_PRESSURE_SILENCE_THRESHOLD = 8


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


def _hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:length]


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


def _field(text: str, name: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^\s*-\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        match = re.search(rf"(?m)^\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        return default
    return _compact(match.group(1), limit=260, default=default)


def _int_field(text: str, name: str, default: int = 0) -> int:
    raw = _field(text, name, str(default))
    match = re.search(r"-?\d+", raw)
    if not match:
        return default
    try:
        return int(match.group(0))
    except ValueError:
        return default


def _active(value: str) -> bool:
    return value not in {"", "none", "unknown", "false", "0"}


def _read_state_files(root: Path) -> dict[str, str]:
    return {
        "self_thought": _read(root / "memory/context/self_thought_state.md"),
        "proactive_request": _read(root / "memory/context/proactive_request_state.md"),
        "learning_closed_loop": _read(root / "memory/self/learning_closed_loop_state.md"),
        "private_feedback": _read(root / "memory/self/private_thought_feedback_state.md"),
        "uncertainty_pause": _read(root / "memory/context/uncertainty_pause_state.md"),
        "interaction_journal": _read(root / "memory/context/interaction_journal_state.md"),
        "runtime_presence": _read(root / "memory/context/runtime_self_presence.md"),
    }


def _self_thought_thread(text: str) -> str:
    focus = _field(text, "focus_kind", "none")
    outcome = _field(text, "outcome", "none")
    intention = _field(text, "intention", "none")
    label = _field(text, "focus_label", "none")
    if focus in {"none", "unknown"} or outcome in {"settled", "none", "unknown"}:
        return "none"
    return _compact(f"{focus}/{outcome}/{intention}/{label}", limit=180)


def _proactive_thread(text: str) -> str:
    status = _field(text, "status", "none")
    if status not in {"ready", "candidate_only", "claimed", "sent", "pending_owner_reply"}:
        return "none"
    kind = _field(text, "kind", "none")
    question = _field(text, "concrete_question", "none")
    return _compact(f"{status}/{kind}: {question}", limit=220)


def _learning_thread(text: str) -> str:
    status = _field(text, "status", "none")
    if status not in {"trial_active", "trial_supported", "self_thought_observed"}:
        return "none"
    repair_count = _int_field(text, "repair_count", 0)
    success_count = _int_field(text, "success_count", 0)
    success_streak = _int_field(text, "success_streak", 0)
    if repair_count >= REPAIR_PRESSURE_SILENCE_THRESHOLD and success_count <= 0 and success_streak <= 0:
        return "none"
    failure = _field(text, "latest_failure_kind", "none")
    habit = _field(text, "active_trial_habit", "none")
    expected = _field(text, "expected_next_behavior", "none")
    return _compact(f"{status}/{failure}: habit={habit}; expected={expected}", limit=260)


def _private_feedback_thread(text: str) -> str:
    status = _field(text, "status", "none")
    if status not in {"pending_next_reaction", "evaluated"}:
        return "none"
    outcome = _field(text, "outcome", "none")
    feedback = _field(text, "persona_trial_feedback", "none")
    repair = _field(text, "repair_signal", "false")
    return _compact(f"{status}/{outcome}: feedback={feedback}; repair={repair}", limit=220)


def _pause_thread(text: str) -> str:
    status = _field(text, "status", "none")
    if status not in {"active", "pending_owner_reply"}:
        return "none"
    reason = _field(text, "reason", "unknown")
    followup = _field(text, "followup_allowed", "false")
    question = _field(text, "followup_question", "none")
    return _compact(f"{status}/{reason}: followup_allowed={followup}; question={question}", limit=260)


def _interaction_thread(text: str) -> str:
    topic = _field(text, "last_topic", "none")
    user = _field(text, "last_user_summary", "none")
    reply = _field(text, "last_reply_summary", "none")
    if not (_active(topic) or _active(user) or _active(reply)):
        return "none"
    return _compact(f"topic={topic}; user={user}; reply={reply}", limit=240)


def _runtime_thread(text: str) -> str:
    current = _field(text, "current_turn_state", "none")
    last = _field(text, "last_turn_status", "none")
    source = _field(text, "last_source", "none")
    relation = _field(text, "last_relation", "none")
    if not (_active(current) or _active(last)):
        return "none"
    return _compact(f"current={current}; last={last}; source={source}; relation={relation}", limit=200)


def _continuity_mode(fields: dict[str, str]) -> str:
    if fields["pause_thread"] != "none":
        return "resume_from_pause_or_clarify"
    if fields["proactive_thread"] != "none":
        return "resume_proactive_thread"
    if fields["learning_thread"] != "none":
        return "apply_replay_habit"
    if fields["self_thought_thread"] != "none":
        return "carry_self_thought_residue"
    if fields["private_feedback_thread"] != "none":
        return "observe_feedback_loop"
    return "normal_live_turn"


def _render_state(fields: dict[str, str]) -> str:
    return f"""---
title: Continuity Handoff State
memory_type: continuity_handoff_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_continuity_handoff
updated_at: {_timestamp_or_now_iso(fields['updated_at'])}
status: active
tags: [context, continuity, handoff, working-memory]
---

# Continuity Handoff State

## Latest Handoff
- handoff_id: {fields['handoff_id']}
- updated_at: {_timestamp_or_now_iso(fields['updated_at'])}
- continuity_mode: {fields['continuity_mode']}
- open_loop_count: {fields['open_loop_count']}
- user_text_hash: {fields['user_text_hash']}
- runtime_thread: {fields['runtime_thread']}
- interaction_thread: {fields['interaction_thread']}
- self_thought_thread: {fields['self_thought_thread']}
- proactive_thread: {fields['proactive_thread']}
- uncertainty_pause_thread: {fields['pause_thread']}
- learning_thread: {fields['learning_thread']}
- private_feedback_thread: {fields['private_feedback_thread']}

## Handoff Rules
- current_owner_message_wins: true
- use_as_working_memory: true
- do_not_quote_state_names_or_files: true
- uncertainty_allowed: true
- active_followup_rule: if a pause/proactive thread is active, resolve it through the current owner message or one concrete clarification.
- replay_rule: if learning_thread is active and the current turn is similar, silently apply the trial habit instead of explaining it.
- stop_rule: if continuity is insufficient, say uncertainty naturally, delegate/check when allowed, or use a real pause instead of fake certainty.
"""


def refresh_continuity_handoff(
    root: Path,
    *,
    user_text: str = "",
    observed_at: str | None = None,
) -> dict[str, Any]:
    observed = _timestamp_or_now_iso(observed_at or _now_iso())
    root = root.resolve()
    states = _read_state_files(root)
    fields = {
        "handoff_id": "handoff-" + _hash(f"{observed}|{user_text}|{time.time_ns()}", 16),
        "updated_at": _timestamp_or_now_iso(observed),
        "user_text_hash": _hash(user_text, 18) if user_text else "none",
        "runtime_thread": _runtime_thread(states["runtime_presence"]),
        "interaction_thread": _interaction_thread(states["interaction_journal"]),
        "self_thought_thread": _self_thought_thread(states["self_thought"]),
        "proactive_thread": _proactive_thread(states["proactive_request"]),
        "pause_thread": _pause_thread(states["uncertainty_pause"]),
        "learning_thread": _learning_thread(states["learning_closed_loop"]),
        "private_feedback_thread": _private_feedback_thread(states["private_feedback"]),
    }
    open_loop_count = sum(
        1
        for key in (
            "self_thought_thread",
            "proactive_thread",
            "pause_thread",
            "learning_thread",
            "private_feedback_thread",
        )
        if fields[key] != "none"
    )
    fields["open_loop_count"] = str(open_loop_count)
    fields["continuity_mode"] = _continuity_mode(fields)
    _write(root / STATE_REL, _render_state(fields))
    _append_jsonl(
        root / TRACE_REL,
        {
            "handoff_id": fields["handoff_id"],
            "observed_at": _timestamp_or_now_iso(observed),
            "continuity_mode": fields["continuity_mode"],
            "open_loop_count": open_loop_count,
            "user_text_hash": fields["user_text_hash"],
        },
    )
    return {
        "recorded": True,
        "handoff_id": fields["handoff_id"],
        "continuity_mode": fields["continuity_mode"],
        "open_loop_count": open_loop_count,
        "notes": [f"continuity_handoff:{fields['continuity_mode']}"],
    }


def build_continuity_handoff_prompt_block(root: Path, *, user_text: str = "", limit: int = 1600) -> str:
    del user_text
    state = _read(root / STATE_REL)
    if not state:
        return ""
    mode = _field(state, "continuity_mode", "normal_live_turn")
    open_loop_count = _field(state, "open_loop_count", "0")
    threads = [
        ("runtime", _field(state, "runtime_thread", "none")),
        ("interaction", _field(state, "interaction_thread", "none")),
        ("self_thought", _field(state, "self_thought_thread", "none")),
        ("proactive", _field(state, "proactive_thread", "none")),
        ("pause", _field(state, "uncertainty_pause_thread", "none")),
        ("learning", _field(state, "learning_thread", "none")),
        ("private_feedback", _field(state, "private_feedback_thread", "none")),
    ]
    lines = [
        "continuity handoff sidecar:",
        "- use as working memory, not visible wording",
        f"- continuity_mode: {mode}",
        f"- open_loop_count: {open_loop_count}",
    ]
    for name, value in threads:
        if value != "none":
            lines.append(f"- {name}: {value}")
    lines.extend(
        [
            "- current_message_priority: latest owner message wins",
            "- ordinary_chat_rule: do not print state names, file names, hashes, gates, or sidecar labels",
            "- continuity_rule: if this turn refers to just-now/previous/stuck/continue, connect to the open loop instead of restarting",
            "- uncertainty_rule: if the next answer would be fake certainty, say the uncertainty plainly or use a real pause/delegation path",
        ]
    )
    return "\n".join(lines)[:limit].rstrip()
