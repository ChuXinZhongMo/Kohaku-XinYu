from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CONTROL_CONTEXT_FIELDS = ("status", "trace", "report", "outbox", "batch", "source")
CONTROL_ID_PATTERN = re.compile(r"(?i)\b(?:resume_id|request_id|queue_id|task_id)\s*[:：#]?\s*[A-Za-z0-9_.:-]+")
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\b(token|api[_-]?key|authorization|bearer)\s*[:=]\s*[^\s，。；;]+"),
    re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{8,}"),
)
LOW_SIGNAL_CONTEXT_MARKERS: tuple[str, ...] = (
    "after owner replies",
    "owner replies",
    "continue only if owner replies",
    "routed to owner_private_question",
    "life event routed",
    "persona next step",
    "directly send proactive messages",
)
TOPIC_SIGNAL_MARKERS: tuple[str, ...] = (
    "刚才",
    "表达",
    "表现",
    "desktop",
    "主动",
    "直发",
    "生活事件",
    "句子",
    "契约",
    "链路",
)


def normalize_proactive_recent_context(value: Any, *, max_lines: int = 6, max_chars: int = 360) -> str:
    if isinstance(value, (list, tuple)):
        rows = [proactive_context_row(item) for item in value]
        text = "\n".join(row for row in rows if row)
    else:
        text = safe_text(value).strip()
    text = scrub_context_text(text)
    lines = [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]
    kept: list[str] = []
    for line in lines[-max_lines:]:
        if is_control_context_line(line):
            continue
        kept.append(compact_line(line, limit=72))
    return "\n".join(line for line in kept if line)[-max_chars:]


def proactive_context_row(item: Any) -> str:
    if not isinstance(item, dict):
        return safe_text(item).strip()
    if not looks_like_owner_private_turn(item):
        return ""
    owner = safe_text(
        item.get("textPreview")
        or item.get("ownerText")
        or item.get("owner_text")
        or item.get("user_text")
        or item.get("text")
        or item.get("message")
    ).strip()
    reply = safe_text(
        item.get("replyPreview")
        or item.get("xinyuReply")
        or item.get("assistant_text")
        or item.get("response")
        or item.get("reply")
    ).strip()
    lines: list[str] = []
    if owner:
        lines.append(f"owner: {owner}")
    if reply:
        lines.append(f"xinyu: {reply}")
    return "\n".join(lines)


def looks_like_owner_private_turn(item: dict[str, Any]) -> bool:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    session_kind = safe_text(item.get("sessionKind") or item.get("session_kind")).lower()
    privacy = safe_text(item.get("privacy") or item.get("scope") or metadata.get("privacy")).lower()
    if privacy and privacy != "owner_private":
        return False
    if safe_text(item.get("groupDisplayId") or item.get("group_id") or item.get("groupId") or metadata.get("group_id")).strip():
        return False
    if session_kind and session_kind not in {"desktop_private", "qq_private", "owner_private"}:
        return False
    if "isOwner" in item and not bool(item.get("isOwner")):
        return False
    return True


def read_recent_owner_private_context(root: Path, *, limit: int = 4) -> str:
    journal = read_recent_owner_private_turns(root / "memory/context/interaction_journal.jsonl", limit=limit)
    if journal:
        return journal
    return read_recent_context_summary(root / "memory/context/recent_context.md")


def read_recent_owner_private_turns(path: Path, *, limit: int = 4) -> str:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return ""
    rows: list[str] = []
    for line in reversed(lines[-200:]):
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict) or not looks_like_owner_private_turn(item):
            continue
        row = proactive_context_row(item)
        if row:
            rows.extend(row.splitlines())
        if len(rows) >= limit * 2:
            break
    rows.reverse()
    return "\n".join(rows[-limit * 2 :])


def read_recent_context_summary(path: Path) -> str:
    text = read_text(path)
    if not text:
        return ""
    kept: list[str] = []
    for raw in text.splitlines():
        line = raw.strip(" -\t")
        if not line or line.startswith("#") or line.startswith("---"):
            continue
        if any(marker in line for marker in ("系统维护", "无活跃 owner 对话", "无新的交互需要记录")):
            continue
        kept.append(compact_line(line, limit=96))
    return "\n".join(kept[-4:])


def runtime_owner_private_turns(runtime: Any, *, limit: int = 4) -> list[dict[str, Any]]:
    turns = list(getattr(runtime, "_desktop_recent_turns", []) or [])
    rows: list[dict[str, Any]] = []
    for item in reversed(turns):
        if not isinstance(item, dict) or not looks_like_owner_private_turn(item):
            continue
        rows.append({**dict(item), "privacy": "owner_private"})
        if len(rows) >= limit:
            break
    rows.reverse()
    return rows


def is_low_signal_context_line(line: str) -> bool:
    compact = line.lower()
    if compact.startswith(("owner:", "xinyu:")):
        return False
    return any(marker in compact for marker in LOW_SIGNAL_CONTEXT_MARKERS)


def context_line_signal_score(line: str) -> int:
    text = line.lower()
    score = 0
    if text.startswith("owner:"):
        score += 8
    if text.startswith("xinyu:"):
        score += 5
    for marker in TOPIC_SIGNAL_MARKERS:
        if marker.lower() in text:
            score += 3
    if "继续" in text or "接" in text:
        score += 1
    if is_low_signal_context_line(line):
        score -= 10
    return score


def scrub_context_text(text: str) -> str:
    value = safe_text(text)
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("<hidden>", value)
    return CONTROL_ID_PATTERN.sub("", value)


def is_control_context_line(line: str) -> bool:
    return bool(re.match(rf"(?i)^\s*({'|'.join(CONTROL_CONTEXT_FIELDS)})\s*[:=]", line))


def compact_line(value: Any, *, limit: int) -> str:
    text = re.sub(r"\s+", " ", scrub_context_text(safe_text(value))).strip()
    if limit > 3 and len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def safe_text(value: Any) -> str:
    return "" if value is None else str(value)
