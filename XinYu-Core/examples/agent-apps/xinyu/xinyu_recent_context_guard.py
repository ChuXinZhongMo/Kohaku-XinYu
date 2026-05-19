from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

from state_service import append_jsonl, atomic_write_text
from xinyu_owner_context_bridge import extract_protected_recent_anchors, merge_protected_recent_anchors


RECENT_CONTEXT_REL = Path("memory/context/recent_context.md")
RECENT_CONTEXT_ANCHOR_REL = Path("memory/context/recent_context_runtime_anchor.md")
INTERACTION_JOURNAL_STATE_REL = Path("memory/context/interaction_journal_state.md")
TRACE_REL = Path("runtime/recent_context_guard_trace.jsonl")
MIN_VALID_RECENT_CONTEXT_CHARS = 160
FUTURE_SKEW_TOLERANCE = timedelta(minutes=15)
STALE_CONTEXT_TOLERANCE = timedelta(minutes=2)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _valid_recent_context(text: str) -> bool:
    clean = text.strip()
    if clean in {"", "---"}:
        return False
    if len(clean) < MIN_VALID_RECENT_CONTEXT_CHARS:
        return False
    return "# Recent Context" in clean or "# 近期上下文" in clean


def _parse_datetime(value: str) -> datetime | None:
    raw = value.strip().strip('"').strip("'")
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    for candidate in (raw, raw.replace(" ", "T", 1)):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.astimezone()
            return parsed
        except ValueError:
            continue
    return None


def _frontmatter_times(text: str) -> list[datetime]:
    times: list[datetime] = []
    for match in re.finditer(r"(?m)^\s*(?:last_updated|updated_at)\s*:\s*(.+?)\s*$", text):
        parsed = _parse_datetime(match.group(1))
        if parsed is not None:
            times.append(parsed)
    return times


def _extract_state_value(text: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*-\s*{re.escape(key)}:\s*(.*?)\s*$", text)
    return match.group(1).strip() if match else ""


def _latest_interaction_at(root: Path) -> datetime | None:
    state = _read(root / INTERACTION_JOURNAL_STATE_REL)
    for key in ("last_owner_private_at", "last_interaction_at"):
        parsed = _parse_datetime(_extract_state_value(state, key))
        if parsed is not None:
            return parsed
    return None


def _has_no_interaction_claim(text: str) -> bool:
    claim_markers = ("全天无交互", "无主人交互", "无对话事件", "静默等待")
    negation_markers = ("不是", "不要", "不能", "不应", "避免")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not any(marker in line for marker in claim_markers):
            continue
        if any(marker in line for marker in negation_markers):
            continue
        return True
    return False


def _recent_context_latest_time(text: str) -> datetime | None:
    times = _frontmatter_times(text)
    return max(times) if times else None


def _invalid_recent_context_reason(text: str, root: Path, now: datetime | None = None) -> str:
    if not _valid_recent_context(text):
        return "invalid_shape"
    checked_at = now or datetime.now().astimezone()
    for timestamp in _frontmatter_times(text):
        if timestamp > checked_at + FUTURE_SKEW_TOLERANCE:
            return "future_timestamp"
    latest = _latest_interaction_at(root)
    context_time = _recent_context_latest_time(text)
    if latest is not None and context_time is not None:
        latest_local = latest.astimezone(context_time.tzinfo)
        if context_time + STALE_CONTEXT_TOLERANCE < latest_local:
            return "stale_latest_interaction"
    if latest is not None and _has_no_interaction_claim(text):
        latest_local = latest.astimezone(checked_at.tzinfo)
        if latest_local.date() == checked_at.date() and latest_local <= checked_at + FUTURE_SKEW_TOLERANCE:
            return "stale_no_interaction_claim"
    return ""


def _build_recent_context_from_interaction_state(root: Path, anchors: list[str]) -> str:
    state = _read(root / INTERACTION_JOURNAL_STATE_REL)
    last_at = _extract_state_value(state, "last_interaction_at") or datetime.now().astimezone().isoformat()
    last_source = _extract_state_value(state, "last_source") or "owner_private"
    last_platform = _extract_state_value(state, "last_platform") or "unknown"
    last_topic = _extract_state_value(state, "last_topic") or "ordinary_chat"
    user_summary = _extract_state_value(state, "last_user_summary") or "unknown"
    reply_summary = _extract_state_value(state, "last_reply_summary") or "unknown"
    continuity_hint = _extract_state_value(state, "continuity_hint") or "recent owner interaction is available"
    text = f"""---
last_updated: "{last_at}"
---

# 近期上下文

## 近期关键事件
- {last_at}: 最新真实交互来自 {last_source}/{last_platform}，主题为 {last_topic}。
- owner 最近一句：{user_summary}
- XinYu 最近回复：{reply_summary}

## 最近状态
- 不能把今天写成无交互或静默等待；运行日志显示刚发生过 owner 私聊。
- {continuity_hint}

## 持续性说明
- 下一轮优先接住 owner 当前句子，再自然延续最新真实对话。
- 不要把后台文件名、状态字段或修复机制直接说给 owner。
"""
    return merge_protected_recent_anchors(text, anchors)


def _trace(root: Path, result: dict[str, str]) -> None:
    try:
        append_jsonl(
            root / TRACE_REL,
            {
                "checked_at": datetime.now().astimezone().isoformat(),
                **result,
            },
        )
    except Exception:
        pass


def ensure_recent_context_health(root: Path) -> dict[str, str]:
    """Keep recent_context from collapsing into an empty prompt fragment."""

    root = root.resolve()
    recent_path = root / RECENT_CONTEXT_REL
    anchor_path = root / RECENT_CONTEXT_ANCHOR_REL
    recent = _read(recent_path)
    anchor = _read(anchor_path)

    recent_problem = _invalid_recent_context_reason(recent, root)
    anchor_problem = _invalid_recent_context_reason(anchor, root)

    if not recent_problem:
        protected_anchors = extract_protected_recent_anchors(anchor) + extract_protected_recent_anchors(recent)
        merged_recent = merge_protected_recent_anchors(recent, protected_anchors)
        action = "anchor_synced"
        if merged_recent != recent.strip():
            atomic_write_text(recent_path, merged_recent)
            recent = merged_recent
            action = "protected_anchors_merged"
        if recent != anchor:
            atomic_write_text(anchor_path, recent)
        result = {"status": "ok", "action": action}
        _trace(root, result)
        return result

    if not anchor_problem:
        protected_anchors = extract_protected_recent_anchors(anchor)
        restored = merge_protected_recent_anchors(anchor, protected_anchors)
        atomic_write_text(recent_path, restored)
        result = {"status": "repaired", "action": f"restored_from_anchor:{recent_problem}"}
        _trace(root, result)
        return result

    latest = _latest_interaction_at(root)
    if latest is not None:
        protected_anchors = extract_protected_recent_anchors(anchor) + extract_protected_recent_anchors(recent)
        restored = _build_recent_context_from_interaction_state(root, protected_anchors)
        atomic_write_text(recent_path, restored)
        atomic_write_text(anchor_path, restored)
        result = {"status": "repaired", "action": f"restored_from_interaction_journal:{recent_problem or 'invalid'}"}
        _trace(root, result)
        return result

    result = {"status": "invalid", "action": "no_valid_anchor"}
    _trace(root, result)
    return result
