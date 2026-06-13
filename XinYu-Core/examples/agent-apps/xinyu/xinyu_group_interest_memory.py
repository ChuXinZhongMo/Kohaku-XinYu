from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import archive_message
from xinyu_group_interest_memory_store import append_group_interest_trace
from xinyu_group_interest_memory_store import read_group_interest_state_json
from xinyu_group_interest_memory_store import write_group_interest_state_json
from xinyu_group_interest_memory_store import write_group_interest_state_markdown
from xinyu_group_social_ids import group_hash, group_member_hash, message_hash


TRACE_REL = Path("runtime/group_interest/group_interest_events.jsonl")
STATE_REL = Path("runtime/group_interest/group_interest_state.json")
STATE_MD_REL = Path("memory/context/group_interest_state.md")

RECENT_KEEP_PER_GROUP = 36
TOPIC_KEEP_PER_GROUP = 24
DEFAULT_ANSWER_WINDOW_SECONDS = 20 * 60

URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
ASCII_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_+#.-]{1,}")

QUESTION_MARKERS = (
    "?",
    "\uff1f",
    "\u5417",
    "\u4e48",
    "\u600e\u4e48",
    "\u4e3a\u4ec0\u4e48",
    "\u4e3a\u5565",
    "\u54ea",
    "\u8c01",
    "\u6c42",
    "\u8bf7\u6559",
)

INTEREST_MARKERS = (
    "AI",
    "LLM",
    "GPT",
    "Codex",
    "NapCat",
    "QQ",
    "API",
    "Python",
    "runtime",
    "bridge",
    "memory",
    "agent",
    "\u8bb0\u5fc6",
    "\u7fa4\u804a",
    "\u4eba\u683c",
    "\u4e3b\u52a8",
    "\u81ea\u4e3b",
    "\u597d\u5947",
    "\u6a21\u578b",
    "\u63d0\u793a\u8bcd",
    "\u8bed\u6c14",
    "\u60c5\u7eea",
    "\u5b66\u4e60",
    "\u4ee3\u7801",
    "\u9879\u76ee",
    "\u6d4b\u8bd5",
    "\u63a5\u53e3",
    "\u684c\u9762",
    "\u81ea\u6211",
    "\u5fc3\u7389",
)

STOP_MARKERS = (
    "\u61c2\u4e86",
    "\u660e\u767d",
    "\u597d\u4e86",
    "\u7b97\u4e86",
    "\u6ca1\u4e8b",
    "\u4e0d\u7528",
    "\u5148\u8fd9\u6837",
    "\u6536\u4f4f",
    "\u4e0d\u804a\u4e86",
)

COMMAND_PREFIXES = ("/", "!", "\uff01", ".", "#")


def _safe_str(value: Any, default: str = "") -> str:
    return default if value is None else str(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _parse_time(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone()


def _seconds_since(value: Any, *, now: datetime | None = None, default: float = 999999.0) -> float:
    parsed = _parse_time(value)
    if parsed is None:
        return default
    current = now or datetime.now().astimezone()
    return max(0.0, (current - parsed).total_seconds())


def _trim(value: Any, *, limit: int = 260) -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if limit > 3 and len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def _hash_text(value: Any, *, length: int = 16) -> str:
    text = _safe_str(value).strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def _read_json(path: Path) -> dict[str, Any]:
    data = read_group_interest_state_json(path)
    if not isinstance(data, dict):
        return {"version": 1, "updated_at": "", "groups": {}}
    data.setdefault("version", 1)
    data.setdefault("groups", {})
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    data["version"] = 1
    data["updated_at"] = _now_iso()
    write_group_interest_state_json(path, data)


def _matched_markers(text: str) -> list[str]:
    lowered = text.lower()
    matched: list[str] = []
    for marker in INTEREST_MARKERS:
        if marker and marker.lower() in lowered:
            matched.append(marker)
    return list(dict.fromkeys(matched))[:8]


def _has_question(text: str) -> bool:
    return any(marker and marker in text for marker in QUESTION_MARKERS)


def _has_stop_signal(text: str) -> bool:
    return any(marker and marker in text for marker in STOP_MARKERS)


def _looks_command_like(text: str) -> bool:
    compact = text.lstrip()
    return bool(compact) and compact.startswith(COMMAND_PREFIXES)


def _topic_key_and_label(text: str, markers: list[str]) -> tuple[str, str]:
    if markers:
        label = ", ".join(markers[:4])
        return "topic-" + _hash_text("|".join(markers[:4]), length=18), label
    ascii_tokens = [token.lower() for token in ASCII_TOKEN_RE.findall(text)]
    if ascii_tokens:
        label = ", ".join(list(dict.fromkeys(ascii_tokens))[:4])
        return "topic-" + _hash_text("|".join(ascii_tokens[:6]), length=18), label
    clean = _trim(text, limit=80)
    return "topic-" + _hash_text(clean, length=18), clean


def _topic_recent_count(group: dict[str, Any], topic_key: str) -> int:
    rows = group.get("recent_messages")
    if not isinstance(rows, list):
        return 0
    return sum(1 for item in rows[-12:] if isinstance(item, dict) and item.get("topic_key") == topic_key)


def _active_thread(group: dict[str, Any]) -> dict[str, Any]:
    active = group.get("active_thread")
    return active if isinstance(active, dict) else {}


def _answer_like_for_active(text: str, active: dict[str, Any], topic_key: str, *, now_dt: datetime) -> bool:
    if _safe_str(active.get("status")) != "waiting_answer":
        return False
    if int(active.get("remaining_followups") or 0) <= 0:
        return False
    if _seconds_since(active.get("last_reply_at"), now=now_dt) > DEFAULT_ANSWER_WINDOW_SECONDS:
        return False
    active_topic = _safe_str(active.get("topic_key"))
    if active_topic and topic_key == active_topic:
        return True
    if len(_trim(text, limit=1000)) >= 6 and not _looks_command_like(text):
        return True
    return False


def analyze_group_interest(text: str, *, group: dict[str, Any] | None = None, triggered: bool = False) -> dict[str, Any]:
    group = group if isinstance(group, dict) else {}
    clean = _trim(text, limit=1000)
    markers = _matched_markers(clean)
    topic_key, topic_label = _topic_key_and_label(clean, markers)
    question = _has_question(clean)
    command_like = _looks_command_like(clean)
    url = bool(URL_RE.search(clean))
    repeated = _topic_recent_count(group, topic_key)
    stop_signal = _has_stop_signal(clean)

    score = 0
    if question:
        score += 3
    score += min(8, len(markers) * 2)
    if repeated >= 1:
        score += 2
    if repeated >= 3:
        score += 2
    if len(clean) >= 18:
        score += 1
    if triggered:
        score += 1
    if url:
        score -= 2
    if command_like:
        score -= 6
    if len(clean) <= 2:
        score -= 4
    if stop_signal:
        score -= 8

    return {
        "score": max(0, score),
        "topic_key": topic_key,
        "topic_label": topic_label,
        "matched_markers": markers,
        "question": question,
        "command_like": command_like,
        "url": url,
        "repeated_topic_count": repeated,
        "stop_signal": stop_signal,
    }


def _reply_decision(
    group: dict[str, Any],
    analysis: dict[str, Any],
    *,
    text: str,
    reply_enabled: bool,
    reply_min_score: int,
    reply_cooldown_seconds: int,
    triggered: bool,
    now_dt: datetime,
) -> dict[str, Any]:
    notes: list[str] = []
    if not reply_enabled:
        return {"should_reply": False, "reply_reason": "group_interest_reply_disabled", "notes": notes}
    if triggered:
        return {"should_reply": False, "reply_reason": "already_triggered_main_turn", "notes": notes}
    if analysis.get("command_like"):
        return {"should_reply": False, "reply_reason": "command_like", "notes": notes}
    if analysis.get("stop_signal"):
        _close_active_thread(group, reason="group_stop_signal")
        return {"should_reply": False, "reply_reason": "group_stop_signal", "notes": ["active_thread_closed"]}

    active = _active_thread(group)
    if _answer_like_for_active(
        text,
        active,
        _safe_str(analysis.get("topic_key")),
        now_dt=now_dt,
    ):
        return {
            "should_reply": True,
            "reply_reason": "group_interest_followup",
            "notes": ["active_thread_followup_allowed"],
        }

    cooldown_elapsed = _seconds_since(group.get("last_interest_reply_at"), now=now_dt)
    if cooldown_elapsed < max(0, int(reply_cooldown_seconds)):
        return {
            "should_reply": False,
            "reply_reason": "group_interest_cooldown",
            "notes": [f"cooldown_remaining:{int(max(0, int(reply_cooldown_seconds) - cooldown_elapsed))}"],
        }
    if int(analysis.get("score") or 0) < max(1, int(reply_min_score)):
        return {"should_reply": False, "reply_reason": "interest_score_below_threshold", "notes": notes}
    return {"should_reply": True, "reply_reason": "group_interest_open", "notes": ["interest_score_passed"]}


def _group_record(state: dict[str, Any], group_id_hash: str, observed_at: str) -> dict[str, Any]:
    groups = state.setdefault("groups", {})
    if not isinstance(groups, dict):
        state["groups"] = {}
        groups = state["groups"]
    group = groups.setdefault(group_id_hash, {})
    group.setdefault("first_seen_at", observed_at)
    group["last_seen_at"] = observed_at
    group.setdefault("recent_messages", [])
    group.setdefault("topics", {})
    return group


def _append_recent_message(group: dict[str, Any], row: dict[str, Any]) -> None:
    recent = group.setdefault("recent_messages", [])
    if not isinstance(recent, list):
        recent = []
        group["recent_messages"] = recent
    recent.append(row)
    if len(recent) > RECENT_KEEP_PER_GROUP:
        del recent[: len(recent) - RECENT_KEEP_PER_GROUP]


def _update_topic(group: dict[str, Any], *, analysis: dict[str, Any], observed_at: str, excerpt: str) -> None:
    topics = group.setdefault("topics", {})
    if not isinstance(topics, dict):
        topics = {}
        group["topics"] = topics
    key = _safe_str(analysis.get("topic_key")) or "topic-unknown"
    topic = topics.setdefault(key, {})
    topic.setdefault("first_seen_at", observed_at)
    topic["last_seen_at"] = observed_at
    topic["label"] = _safe_str(analysis.get("topic_label"))
    topic["count"] = int(topic.get("count") or 0) + 1
    topic["score"] = max(int(topic.get("score") or 0), int(analysis.get("score") or 0))
    topic["latest_excerpt"] = excerpt
    if len(topics) > TOPIC_KEEP_PER_GROUP:
        ordered = sorted(topics.items(), key=lambda item: _safe_str(item[1].get("last_seen_at")))
        for stale_key, _ in ordered[: len(topics) - TOPIC_KEEP_PER_GROUP]:
            topics.pop(stale_key, None)


def _archive_ambient_group_message(
    root: Path,
    *,
    event: dict[str, Any],
    text: str,
    analysis: dict[str, Any],
    observed_at: str,
) -> int | None:
    if analysis.get("command_like") or len(_trim(text, limit=1000)) <= 2:
        return None
    platform = _safe_str(event.get("platform"), "qq") or "qq"
    group_id = _safe_str(event.get("group_id")).strip()
    user_id = _safe_str(event.get("user_id")).strip()
    payload = {
        "platform": platform,
        "message_type": "group_shadow_text",
        "group_id": group_id,
        "user_id": user_id,
        "session_id": f"{platform}:group:{group_id}:{user_id or 'unknown'}",
        "message_id": _safe_str(event.get("message_id")).strip(),
        "timestamp": event.get("time"),
        "metadata": {
            "source": "qq_group_interest_observation",
            "privacy_scope": "group_context",
            "qq_group_shadow_archive": True,
            "qq_group_interest_score": int(analysis.get("score") or 0),
            "qq_group_interest_topic_key": _safe_str(analysis.get("topic_key")),
            "stable_memory_write": "blocked",
            "owner_relationship_write": "blocked",
            "is_owner_user": False,
        },
    }
    return archive_message(
        root,
        payload,
        role="user",
        text=text,
        created_at=observed_at,
        message_type="group_shadow_text",
        source_event_id=_safe_str(event.get("message_id")).strip(),
        quality_flags={"flags": ["ambient_group_observation", "stable_memory_write_blocked"]},
    )


def _close_active_thread(group: dict[str, Any], *, reason: str) -> None:
    group["active_thread"] = {
        "status": "idle",
        "topic_key": "",
        "topic_label": "",
        "remaining_followups": 0,
        "questions_asked": 0,
        "stop_reason": reason,
        "updated_at": _now_iso(),
    }


def _write_state_projection(root: Path, state: dict[str, Any], latest: dict[str, Any]) -> None:
    groups = state.get("groups") if isinstance(state.get("groups"), dict) else {}
    latest_group = groups.get(_safe_str(latest.get("group_hash")), {}) if isinstance(groups, dict) else {}
    active = latest_group.get("active_thread") if isinstance(latest_group, dict) else {}
    active = active if isinstance(active, dict) else {}
    topics = latest_group.get("topics") if isinstance(latest_group, dict) else {}
    recent_topics = sorted(
        [item for item in (topics or {}).values() if isinstance(item, dict)],
        key=lambda item: _safe_str(item.get("last_seen_at")),
        reverse=True,
    )[:5]
    topic_lines = [
        f"- {_safe_str(item.get('label')) or 'unknown'} count={int(item.get('count') or 0)} score={int(item.get('score') or 0)}"
        for item in recent_topics
    ] or ["- none"]
    content = "\n".join(
        [
            "---",
            "title: Group Interest State",
            "memory_type: group_interest_state",
            "time_scope: short_term",
            "privacy_scope: group_context",
            "protected: true",
            "source: xinyu_group_interest_memory",
            f"updated_at: {_now_iso()}",
            "stable_memory_write: blocked",
            "owner_relationship_write: blocked",
            "---",
            "",
            "# Group Interest State",
            "",
            "## Latest Observation",
            f"- observed_at: {_safe_str(latest.get('observed_at'))}",
            f"- group_hash: {_safe_str(latest.get('group_hash'))}",
            f"- actor_member_hash: {_safe_str(latest.get('actor_member_hash'))}",
            f"- topic_label: {_safe_str(latest.get('topic_label')) or 'none'}",
            f"- interest_score: {int(latest.get('interest_score') or 0)}",
            f"- reply_reason: {_safe_str(latest.get('reply_reason')) or 'none'}",
            f"- should_reply: {str(bool(latest.get('should_reply'))).lower()}",
            "",
            "## Active Thread",
            f"- status: {_safe_str(active.get('status')) or 'idle'}",
            f"- topic_label: {_safe_str(active.get('topic_label')) or 'none'}",
            f"- remaining_followups: {int(active.get('remaining_followups') or 0)}",
            f"- stop_reason: {_safe_str(active.get('stop_reason')) or 'none'}",
            "",
            "## Recent Topics",
            *topic_lines,
            "",
            "## Boundary",
            "- group text is group_context, not owner_private memory.",
            "- stable memory promotion remains blocked unless an existing review gate approves it.",
            "- proactive group replies are bounded by whitelist, interest threshold, cooldown, and followup budget.",
        ]
    )
    write_group_interest_state_markdown(root / STATE_MD_REL, content.rstrip() + "\n")


def observe_group_interest(
    root: Path,
    *,
    event: dict[str, Any],
    text: str,
    normalized_text: str = "",
    triggered: bool = False,
    reply_enabled: bool = False,
    reply_min_score: int = 7,
    reply_cooldown_seconds: int = 900,
    followup_max_turns: int = 2,
    max_text_chars: int = 260,
) -> dict[str, Any]:
    del followup_max_turns
    root = Path(root)
    platform = _safe_str(event.get("platform"), "qq") or "qq"
    raw_group_id = _safe_str(event.get("group_id")).strip()
    raw_user_id = _safe_str(event.get("user_id")).strip()
    raw_message_id = _safe_str(event.get("message_id")).strip()
    if not raw_group_id:
        return {"recorded": False, "should_reply": False, "notes": ["group_interest_missing_group_id"]}

    clean_text = _trim(normalized_text or text, limit=max(40, int(max_text_chars)))
    if not clean_text:
        return {"recorded": False, "should_reply": False, "notes": ["group_interest_empty_text"]}

    observed_at = _now_iso()
    now_dt = _parse_time(observed_at) or datetime.now().astimezone()
    state_path = root / STATE_REL
    state = _read_json(state_path)
    g_hash = group_hash(platform, raw_group_id)
    actor_hash = group_member_hash(platform, raw_group_id, raw_user_id)
    msg_hash = message_hash(platform, raw_group_id, raw_message_id)
    group = _group_record(state, g_hash, observed_at)

    analysis = analyze_group_interest(clean_text, group=group, triggered=triggered)
    decision = _reply_decision(
        group,
        analysis,
        text=clean_text,
        reply_enabled=reply_enabled,
        reply_min_score=reply_min_score,
        reply_cooldown_seconds=reply_cooldown_seconds,
        triggered=triggered,
        now_dt=now_dt,
    )
    row = {
        "observed_at": observed_at,
        "source": "qq_group_interest_memory",
        "privacy_scope": "group_context",
        "stable_memory_write": "blocked",
        "owner_relationship_write": "blocked",
        "reply_policy": "candidate_gated" if decision.get("should_reply") else "observe",
        "group_hash": g_hash,
        "actor_member_hash": actor_hash,
        "message_hash": msg_hash,
        "triggered": bool(triggered),
        "text_excerpt": clean_text,
        "topic_key": _safe_str(analysis.get("topic_key")),
        "topic_label": _safe_str(analysis.get("topic_label")),
        "interest_score": int(analysis.get("score") or 0),
        "matched_markers": analysis.get("matched_markers") if isinstance(analysis.get("matched_markers"), list) else [],
        "question": bool(analysis.get("question")),
        "repeated_topic_count": int(analysis.get("repeated_topic_count") or 0),
        "should_reply": bool(decision.get("should_reply")),
        "reply_reason": _safe_str(decision.get("reply_reason")),
    }

    _append_recent_message(
        group,
        {
            "observed_at": observed_at,
            "actor_member_hash": actor_hash,
            "message_hash": msg_hash,
            "topic_key": row["topic_key"],
            "topic_label": row["topic_label"],
            "interest_score": row["interest_score"],
            "text_excerpt": clean_text,
        },
    )
    _update_topic(group, analysis=analysis, observed_at=observed_at, excerpt=clean_text)
    archive_message_id: int | None = None
    if not triggered and not decision.get("should_reply"):
        archive_message_id = _archive_ambient_group_message(
            root,
            event=event,
            text=clean_text,
            analysis=analysis,
            observed_at=observed_at,
        )
    row["archive_message_id"] = archive_message_id

    try:
        append_group_interest_trace(root / TRACE_REL, row)
        _write_json(state_path, state)
        _write_state_projection(root, state, row)
    except OSError as exc:
        return {
            "recorded": False,
            "should_reply": bool(decision.get("should_reply")),
            "reply_reason": _safe_str(decision.get("reply_reason")),
            "notes": [f"group_interest_write_error:{type(exc).__name__}"],
            "row": row,
        }

    notes = ["group_interest_observed", *list(decision.get("notes") or [])]
    if archive_message_id is not None:
        notes.append("group_ambient_archive_written")
    elif not triggered and decision.get("should_reply"):
        notes.append("archive_deferred_to_live_turn")
    return {
        "recorded": True,
        "should_reply": bool(decision.get("should_reply")),
        "reply_reason": _safe_str(decision.get("reply_reason")),
        "topic_key": row["topic_key"],
        "topic_label": row["topic_label"],
        "interest_score": row["interest_score"],
        "archive_message_id": archive_message_id,
        "notes": notes,
        "row": row,
    }


def group_interest_metadata(observation: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(observation, dict) or not observation.get("should_reply"):
        return {}
    return {
        "qq_group_interest_reply": True,
        "qq_group_interest_reply_reason": _safe_str(observation.get("reply_reason")),
        "qq_group_interest_topic_key": _safe_str(observation.get("topic_key")),
        "qq_group_interest_topic_label": _safe_str(observation.get("topic_label")),
        "qq_group_interest_score": int(observation.get("interest_score") or 0),
        "qq_group_interest_stop_policy": "ask at most one useful question, then stop after the answer or followup budget",
    }


def record_group_interest_reply(
    root: Path,
    *,
    payload: dict[str, Any],
    reply: str,
    followup_max_turns: int = 2,
    sent_at: str | None = None,
) -> dict[str, Any]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    if not metadata.get("qq_group_interest_reply"):
        return {"recorded": False, "notes": ["not_group_interest_reply"]}
    group_id = _safe_str(payload.get("group_id")).strip()
    if not group_id:
        return {"recorded": False, "notes": ["missing_group_id"]}
    root = Path(root)
    platform = _safe_str(payload.get("platform"), "qq") or "qq"
    g_hash = group_hash(platform, group_id)
    state_path = root / STATE_REL
    state = _read_json(state_path)
    now = sent_at or _now_iso()
    group = _group_record(state, g_hash, now)
    active = _active_thread(group)
    reason = _safe_str(metadata.get("qq_group_interest_reply_reason"))
    topic_key = _safe_str(metadata.get("qq_group_interest_topic_key"))
    topic_label = _safe_str(metadata.get("qq_group_interest_topic_label"))
    asks_question = _has_question(reply)
    max_followups = max(0, int(followup_max_turns))
    if asks_question and max_followups > 0:
        previous_remaining = int(active.get("remaining_followups") or max_followups)
        remaining = previous_remaining if reason == "group_interest_open" else max(0, previous_remaining - 1)
        if remaining > 0:
            group["active_thread"] = {
                "status": "waiting_answer",
                "topic_key": topic_key,
                "topic_label": topic_label,
                "last_reply_at": now,
                "remaining_followups": remaining,
                "questions_asked": int(active.get("questions_asked") or 0) + 1,
                "stop_reason": "",
                "updated_at": now,
            }
        else:
            _close_active_thread(group, reason="followup_budget_exhausted")
    else:
        _close_active_thread(group, reason="reply_no_open_question")
    group["last_interest_reply_at"] = now
    row = {
        "observed_at": now,
        "source": "qq_group_interest_reply",
        "group_hash": g_hash,
        "topic_key": topic_key,
        "topic_label": topic_label,
        "reply_reason": reason,
        "reply_asked_question": asks_question,
        "active_status": _safe_str(_active_thread(group).get("status"), "idle"),
        "stable_memory_write": "blocked",
        "owner_relationship_write": "blocked",
    }
    try:
        append_group_interest_trace(root / TRACE_REL, row)
        _write_json(state_path, state)
        _write_state_projection(root, state, row)
    except OSError as exc:
        return {"recorded": False, "notes": [f"group_interest_reply_write_error:{type(exc).__name__}"]}
    return {"recorded": True, "notes": ["group_interest_reply_recorded"], "row": row}
