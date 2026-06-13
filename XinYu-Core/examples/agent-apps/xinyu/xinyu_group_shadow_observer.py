from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_group_shadow_observer_store import append_group_shadow_trace
from xinyu_group_shadow_observer_store import read_group_shadow_history_text
from xinyu_group_shadow_observer_store import write_group_shadow_history_text
from xinyu_group_shadow_observer_store import write_group_shadow_state


TRACE_REL = Path("runtime/group_shadow/group_shadow_observations.jsonl")
HISTORY_REL = Path("runtime/group_shadow/group_shadow_recent_messages.jsonl")
STATE_REL = Path("memory/context/group_shadow_state.md")
HISTORY_KEEP_PER_GROUP = 12
STATE_HISTORY_ITEMS = 6

STYLE_PRESSURE_MARKERS = (
    "AI味",
    "太AI",
    "像AI",
    "GPT味",
    "机械",
    "模板",
    "模版",
    "客服",
    "接待腔",
    "不像人",
)

COMMAND_PREFIXES = ("/", "!", "！", ".", "#")
URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _hash_id(value: Any, *, length: int = 16) -> str:
    text = _safe_str(value).strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return _now_iso()
    return parsed.astimezone().isoformat(timespec="seconds")


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


def _trim(text: Any, limit: int = 260) -> str:
    clean = re.sub(r"\s+", " ", _safe_str(text)).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def _contains_any(text: str, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if marker and marker in text]


def classify_group_shadow_message(text: str, *, triggered: bool) -> dict[str, Any]:
    clean = _trim(text, limit=1000)
    compact = re.sub(r"\s+", "", clean)
    markers = {
        "style_pressure": _contains_any(clean, STYLE_PRESSURE_MARKERS),
        "url": ["url"] if URL_RE.search(clean) else [],
        "command_like": ["command_prefix"] if compact.startswith(COMMAND_PREFIXES) else [],
        "question": ["question"] if "?" in clean or "？" in clean else [],
    }
    risk_flags: list[str] = []
    if len(clean) <= 2:
        risk_flags.append("too_short_to_learn")
    if markers["command_like"]:
        risk_flags.append("command_like")
    if not triggered and len(clean) < 6:
        risk_flags.append("untriggered_short_chatter")
    if markers["style_pressure"]:
        risk_flags.append("style_pressure_in_group")
    if triggered:
        learning_candidate = "triggered_reply_context"
    elif markers["url"] or markers["question"] or len(clean) >= 18:
        learning_candidate = "ambient_social_context"
    else:
        learning_candidate = "low_signal_chatter"
    return {
        "text_chars": len(clean),
        "markers": markers,
        "risk_flags": risk_flags,
        "learning_candidate": learning_candidate,
    }


def record_group_shadow_observation(
    root: Path,
    *,
    event: dict[str, Any],
    text: str,
    normalized_text: str = "",
    triggered: bool = False,
    trigger_reason: str = "",
    allowed_group: bool = False,
    prepare_reason: str = "",
    max_text_chars: int = 260,
) -> dict[str, Any]:
    root = Path(root)
    raw_group_id = _safe_str(event.get("group_id")).strip()
    raw_user_id = _safe_str(event.get("user_id")).strip()
    raw_message_id = _safe_str(event.get("message_id")).strip()
    group_hash = _hash_id(raw_group_id)
    actor_hash = _hash_id(raw_user_id)
    message_hash = _hash_id(raw_message_id)
    observed_at = _timestamp_or_now_iso(_now_iso())
    clean_text = _trim(text, limit=max(40, int(max_text_chars)))
    classification = classify_group_shadow_message(normalized_text or text, triggered=triggered)
    recent_context = _recent_group_context(root, group_hash=group_hash, limit=STATE_HISTORY_ITEMS)
    trace_path = root / TRACE_REL
    row = {
        "observed_at": _timestamp_or_now_iso(observed_at),
        "source": "qq_gateway_group_shadow",
        "reply_policy": "no_reply_shadow_only",
        "stable_memory_write": "blocked",
        "owner_relationship_write": "blocked",
        "group_id_hash": group_hash,
        "actor_hash": actor_hash,
        "message_id_hash": message_hash,
        "allowed_group": bool(allowed_group),
        "triggered": bool(triggered),
        "trigger_reason": _safe_str(trigger_reason),
        "prepare_reason": _safe_str(prepare_reason),
        "text_excerpt": clean_text,
        "normalized_text_excerpt": _trim(normalized_text or text, limit=max(40, int(max_text_chars))),
        "recent_group_context_count": len(recent_context),
        "recent_group_context": recent_context,
        **classification,
    }
    append_group_shadow_trace(trace_path, row)
    _append_recent_history(
        root,
        {
            "observed_at": _timestamp_or_now_iso(observed_at),
            "group_id_hash": group_hash,
            "actor_hash": actor_hash,
            "message_id_hash": message_hash,
            "triggered": bool(triggered),
            "text_excerpt": clean_text,
            "learning_candidate": _safe_str(classification.get("learning_candidate")),
        },
    )
    _write_state(root, row)
    return {
        "recorded": True,
        "path": str(trace_path),
        "notes": ["group_shadow_observed", "no_reply", "stable_memory_write_blocked"],
        "row": row,
    }


def _recent_group_context(root: Path, *, group_hash: str, limit: int = STATE_HISTORY_ITEMS) -> list[dict[str, Any]]:
    if not group_hash:
        return []
    rows = [
        row
        for row in _read_history_rows(root / HISTORY_REL)
        if _safe_str(row.get("group_id_hash")) == group_hash
    ]
    return rows[-max(0, int(limit)) :]


def _append_recent_history(root: Path, row: dict[str, Any]) -> None:
    path = root / HISTORY_REL
    rows = _read_history_rows(path)
    rows.append(row)
    grouped: dict[str, list[dict[str, Any]]] = {}
    ordered_groups: list[str] = []
    for item in rows:
        group_hash = _safe_str(item.get("group_id_hash"))
        if not group_hash:
            continue
        if group_hash not in grouped:
            grouped[group_hash] = []
            ordered_groups.append(group_hash)
        grouped[group_hash].append(item)
    compact_rows: list[dict[str, Any]] = []
    for group_hash in ordered_groups:
        compact_rows.extend(grouped[group_hash][-HISTORY_KEEP_PER_GROUP:])
    lines = [json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str) for item in compact_rows]
    write_group_shadow_history_text(path, "\n".join(lines))


def _read_history_rows(path: Path) -> list[dict[str, Any]]:
    text = read_group_shadow_history_text(path)
    if not text:
        return []
    lines = text.splitlines()
    rows: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _write_state(root: Path, row: dict[str, Any]) -> None:
    state_path = root / STATE_REL
    history_lines = _state_history_lines(row.get("recent_group_context") or [])
    content = "\n".join(
        [
            "---",
            "title: Group Shadow State",
            "memory_type: group_shadow_state",
            "time_scope: short_term",
            "subject_ids: [xinyu]",
            "protected: true",
            "source: xinyu_group_shadow_observer",
            f"updated_at: {_timestamp_or_now_iso(row.get('observed_at'))}",
            "status: active",
            "tags: [runtime, group, shadow, no-reply]",
            "---",
            "",
            "# Group Shadow State",
            "",
            "## Latest Observation",
            f"- observed_at: {_timestamp_or_now_iso(row.get('observed_at'))}",
            f"- group_id_hash: {_safe_str(row.get('group_id_hash'))}",
            f"- actor_hash: {_safe_str(row.get('actor_hash'))}",
            f"- triggered: {str(bool(row.get('triggered'))).lower()}",
            f"- trigger_reason: {_safe_str(row.get('trigger_reason')) or 'none'}",
            f"- learning_candidate: {_safe_str(row.get('learning_candidate'))}",
            f"- risk_flags: {', '.join(row.get('risk_flags') or []) or 'none'}",
            f"- text_excerpt: {_safe_str(row.get('text_excerpt'))}",
            "",
            "## Recent Group Context",
            *history_lines,
            "",
            "## Boundary",
            "- reply_policy: no_reply_shadow_only",
            "- stable_memory_write: blocked",
            "- owner_relationship_write: blocked",
            "- use: observe group social texture before enabling active replies",
        ]
    )
    write_group_shadow_state(state_path, content)


def _state_history_lines(rows: Any) -> list[str]:
    items = rows if isinstance(rows, list) else []
    if not items:
        return ["- none"]
    lines: list[str] = []
    for item in items[-STATE_HISTORY_ITEMS:]:
        if not isinstance(item, dict):
            continue
        observed_at = _safe_str(item.get("observed_at")) or "unknown_time"
        actor_hash = _safe_str(item.get("actor_hash")) or "unknown_actor"
        excerpt = _safe_str(item.get("text_excerpt"))
        if excerpt:
            lines.append(f"- {observed_at} actor:{actor_hash} text: {excerpt}")
    return lines or ["- none"]
