from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any


STATE_REL = Path("memory/context/interaction_journal_state.md")
LOG_REL = Path("memory/context/interaction_journal.jsonl")
MAX_LOG_ROWS = 240

_LOCAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+")
_LONG_NUMERIC_ID_RE = re.compile(r"\b\d{8,}\b")

RUNTIME_MARKERS = (
    "运行",
    "程序",
    "状态",
    "心跳",
    "日志",
    "桥接",
    "自己怎么看",
    "自身",
    "醒着",
    "Codex",
    "codex",
)
PERSONA_MARKERS = (
    "人格",
    "像人",
    "模板",
    "机械",
    "接待腔",
    "自然",
    "说话",
    "感情",
)
TECH_MARKERS = (
    "代码",
    "实现",
    "测试",
    "修复",
    "模块",
    "架构",
    "文件",
    "bug",
    "plan",
)
DREAM_MARKERS = ("梦", "梦境", "反思", "残留")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _timestamp_or_now_iso(value: Any = None) -> str:
    text = _safe_str(value).strip()
    if not text:
        return _now_iso()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return _now_iso()
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat()


def _hash_text(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:length]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    lowered = str(value or "").strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _scrub(value: Any, *, limit: int = 180, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    text = _LOCAL_PATH_RE.sub("[local-path]", text)
    text = _LONG_NUMERIC_ID_RE.sub("[id]", text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _source_scope(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    is_owner = _as_bool(payload.get("is_owner_user") or metadata.get("is_owner_user"), default=False)
    group_id = _safe_str(payload.get("group_id")).strip()
    message_type = _safe_str(payload.get("message_type")).strip().lower()
    if is_owner and not group_id and not message_type.startswith("group"):
        return "owner_private"
    if is_owner and (group_id or message_type.startswith("group")):
        return "owner_group"
    if group_id or message_type.startswith("group"):
        return "group_context"
    if message_type.startswith("system"):
        return "system"
    return "external_private"


def _topic_label(user_text: str, reply: str, turn_kind: str) -> str:
    combined = f"{user_text}\n{reply}"
    if "technical" in turn_kind or _contains_any(combined, TECH_MARKERS):
        return "technical_work"
    if _contains_any(combined, RUNTIME_MARKERS):
        return "runtime_self_awareness"
    if _contains_any(combined, PERSONA_MARKERS):
        return "persona_and_voice"
    if _contains_any(combined, DREAM_MARKERS):
        return "dream_or_reflection"
    return "ordinary_chat"


def _load_rows(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-MAX_LOG_ROWS:]:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    trimmed = rows[-MAX_LOG_ROWS:]
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in trimmed),
        encoding="utf-8",
    )


def _parse_iso(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _minutes_between(later: str, earlier: Any) -> str:
    later_dt = _parse_iso(later)
    earlier_dt = _parse_iso(earlier)
    if later_dt is None or earlier_dt is None:
        return "unknown"
    return str(max(0, int((later_dt - earlier_dt).total_seconds() // 60)))


def _render_state(*, row: dict[str, Any], rows: list[dict[str, Any]], updated_at: str) -> str:
    recent = rows[-20:]
    owner_rows = [item for item in recent if _safe_str(item.get("source_scope")).startswith("owner")]
    last_owner = next((item for item in reversed(rows) if _safe_str(item.get("source_scope")).startswith("owner")), None)
    last_owner_at = _safe_str(last_owner.get("finished_at")) if last_owner else "none"
    minutes_since_owner = _minutes_between(updated_at, last_owner_at) if last_owner else "unknown"
    last_topic = _scrub(row.get("topic"), limit=80)
    continuity_hint = (
        f"last {row.get('source_scope')} turn was about {last_topic}; "
        f"last owner/private turn was {minutes_since_owner} minutes ago"
    )
    return f"""---
title: Runtime Interaction Journal State
memory_type: interaction_journal_state
time_scope: immediate_runtime
subject_ids: [xinyu]
protected: true
source: xinyu_interaction_journal
updated_at: {updated_at}
status: active
tags: [runtime, interaction, continuity, heartbeat]
---

# Runtime Interaction Journal State

## Latest Real Interaction
- status: active
- last_interaction_at: {updated_at}
- last_source: {_scrub(row.get('source_scope'), limit=80)}
- last_platform: {_scrub(row.get('platform'), limit=80)}
- last_topic: {last_topic}
- last_turn_kind: {_scrub(row.get('turn_kind'), limit=100)}
- last_reply_elapsed_ms: {_scrub(row.get('reply_elapsed_ms'), limit=40)}
- last_reply_chars: {_scrub(row.get('reply_chars'), limit=40)}
- last_session_hash: {_scrub(row.get('session_hash'), limit=80)}
- last_user_summary: {_scrub(row.get('user_preview'), limit=150)}
- last_reply_summary: {_scrub(row.get('reply_preview'), limit=150)}

## Recent Continuity
- recent_interaction_count: {len(recent)}
- recent_owner_private_count: {len(owner_rows)}
- last_owner_private_at: {_scrub(last_owner_at, limit=80)}
- minutes_since_last_owner_private: {minutes_since_owner}
- continuity_hint: {_scrub(continuity_hint, limit=220)}

## Boundary
- reality_source: real_bridge_chat_turn
- dream_or_reflection_source: no
- stable_memory_write: no
- readable_by: live_turn_runtime_presence, self_thought_loop, private_thought_event
"""


def record_interaction_turn(
    root: Path,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    session_key: str,
    source: str = "qq_gateway",
    turn_kind: str = "unknown",
    turn_id: str = "",
    elapsed_ms: int | None = None,
    finished_at: str | None = None,
) -> dict[str, Any]:
    updated = _timestamp_or_now_iso(finished_at)
    source_scope = _source_scope(payload)
    row = {
        "interaction_id": "interaction-" + _hash_text(f"{session_key}|{updated}|{time.time_ns()}", 18),
        "event_time": updated,
        "finished_at": updated,
        "source": _scrub(source, limit=80),
        "source_scope": source_scope,
        "platform": _scrub(payload.get("platform") or "unknown", limit=80),
        "message_type": _scrub(payload.get("message_type") or "unknown", limit=80),
        "session_hash": _hash_text(session_key, 18),
        "turn_id": _scrub(turn_id, limit=80),
        "turn_kind": _scrub(turn_kind, limit=100),
        "topic": _topic_label(user_text, reply, turn_kind),
        "user_preview": _scrub(user_text, limit=180),
        "reply_preview": _scrub(reply, limit=180),
        "reply_elapsed_ms": int(elapsed_ms or 0),
        "reply_chars": len(reply or ""),
    }
    rows = _load_rows(root / LOG_REL)
    rows.append(row)
    _write_rows(root / LOG_REL, rows)
    state = _render_state(row=row, rows=rows, updated_at=_timestamp_or_now_iso(updated))
    state_path = root / STATE_REL
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(state.rstrip() + "\n", encoding="utf-8")
    return {
        "recorded": True,
        "interaction_id": row["interaction_id"],
        "topic": row["topic"],
        "source_scope": source_scope,
        "notes": ["interaction_journal_recorded", f"interaction_topic:{row['topic']}"],
    }


def read_interaction_journal_state(root: Path) -> str:
    try:
        return (root / STATE_REL).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""
