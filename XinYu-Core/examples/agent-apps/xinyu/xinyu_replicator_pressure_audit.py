"""Lightweight replicator-pressure audit: alert only, no memory writes."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from xinyu_action_openended_audit import run_audit


LIFE_NARRATIVE_MARKERS = (
    "我在成长",
    "生命结构",
    "自我涌现",
    "像活了",
    "触碰现实",
    "stepping stone",
    "开放式生长",
)
TOOL_SPAM_MARKERS = ("codex_delegate", "log_scan", "status_probe")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _level_from_score(score: int) -> str:
    if score >= 6:
        return "alert"
    if score >= 3:
        return "watch"
    return "quiet"


def assess_replicator_pressure(root: Path, *, audit_result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read-only replicator pressure check. Never writes memory or runtime state."""
    root = root.resolve()
    audit = audit_result if isinstance(audit_result, dict) else run_audit(root)
    signals: list[str] = []
    score = 0

    for warning in audit.get("warnings") or []:
        text = _safe_str(warning)
        if text.startswith("repeated_visible_phrase:"):
            count_match = re.search(r"count=(\d+)", text)
            count = int(count_match.group(1)) if count_match else 0
            if count >= 3:
                signals.append(f"visible_phrase_repeat:{count}")
                score += min(3, count - 1)
        if text.startswith("repeated_action_theme:"):
            count_match = re.search(r"count=(\d+)", text)
            count = int(count_match.group(1)) if count_match else 0
            if count >= 4:
                signals.append(f"action_theme_repeat:{count}")
                score += min(3, count - 2)

    phrase_items = audit.get("top_repeated_visible_phrases") or []
    theme_items = audit.get("top_repeated_action_themes") or []
    if phrase_items and int(phrase_items[0].get("count") or 0) >= 3:
        signals.append("top_phrase_cluster")
        score += 1
    if theme_items and int(theme_items[0].get("count") or 0) >= 4:
        signals.append("top_theme_cluster")
        score += 1

    shadow_text = _read_tail(root / "runtime/answer_discipline_visible_send_shadow.jsonl", lines=40)
    narrative_hits = sum(1 for marker in LIFE_NARRATIVE_MARKERS if marker.lower() in shadow_text.lower())
    if narrative_hits >= 2:
        signals.append(f"life_narrative_markers:{narrative_hits}")
        score += narrative_hits

    tool_hits = Counter()
    for marker in TOOL_SPAM_MARKERS:
        tool_hits[marker] = shadow_text.lower().count(marker.lower())
    dominant_tool = tool_hits.most_common(1)[0] if tool_hits else ("", 0)
    if dominant_tool[1] >= 4:
        signals.append(f"tool_call_motif:{dominant_tool[0]}:{dominant_tool[1]}")
        score += 2

    level = _level_from_score(score)
    return {
        "level": level,
        "score": score,
        "signals": signals,
        "memory_write": False,
        "action": "alert_only",
        "notes": ["replicator_pressure_read_only"],
    }


def _read_tail(path: Path, *, lines: int = 40) -> str:
    if not path.exists():
        return ""
    try:
        content = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(content[-lines:])