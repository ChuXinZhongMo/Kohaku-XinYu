from __future__ import annotations

import re
from typing import Any


RESULT_LABELS = {
    "success": "已完成",
    "failure": "执行失败",
    "failed": "执行失败",
    "timeout": "执行超时",
    "timed_out": "执行超时",
    "blocked_by_boundary": "边界拦住",
    "blocked": "边界拦住",
    "unknown": "结果未知",
}

PRESSURE_LABELS = {
    "low": "低负载",
    "medium": "中负载",
    "high": "高负载",
    "unknown": "负载未知",
}

TOOL_ARTIFACT_VISIBLE_LABEL = "系统工具输出记录（已忽略）"

TOOL_ARTIFACT_MARKERS = (
    "[Tool batch completed]",
    "[Tool result]",
    "[Tool call]",
    "[Tool output]",
    "Tool batch completed",
    "COMMAND:",
    "EXIT_CODE:",
    "=== STDOUT ===",
    "=== STDERR ===",
)

TOOL_ARTIFACT_PATTERNS = (
    re.compile(r"\[Tool batch completed\][^\r\n。]*", re.I),
    re.compile(r"\[Tool (?:result|call|output)[^\]]*\][^\r\n。]*", re.I),
    re.compile(r"##\s*read(?:_[0-9A-Fa-f]{6,})?\s*-\s*OK\s+\d+[^\r\n。]*", re.I),
    re.compile(r"\bOK\s+\d+\s*(?:→|->)[^\r\n。]*", re.I),
    re.compile(r"(?m)^\s*(?:COMMAND|EXIT_CODE):[^\r\n]*$", re.I),
    re.compile(r"(?m)^\s*===\s*(?:STDOUT|STDERR)\s*===\s*$", re.I),
)


def visible_text_has_tool_artifact(value: Any) -> bool:
    text = "" if value is None else str(value)
    if not text:
        return False
    lowered = text.lower()
    if TOOL_ARTIFACT_VISIBLE_LABEL in text:
        return True
    if any(marker.lower() in lowered for marker in TOOL_ARTIFACT_MARKERS):
        return True
    return any(pattern.search(text) for pattern in TOOL_ARTIFACT_PATTERNS)


def sanitize_visible_text(value: Any) -> str:
    text = "" if value is None else str(value)
    if not text:
        return ""
    text = _sanitize_tool_artifacts(text)
    text = re.sub(
        r"local action pressure after\s+codex_delegate(?::[^\s;，。]+)?",
        "Codex 委派的行动残留",
        text,
        flags=re.I,
    )
    text = re.sub(r"\bcodex_delegate(?::[^\s;，。]+)?\b", "Codex 委派", text, flags=re.I)
    text = re.sub(
        r"local action pressure after\s+status_probe(?::[^\s;，。]+)?",
        "状态检查的行动残留",
        text,
        flags=re.I,
    )
    text = re.sub(r"\bstatus_probe(?::[^\s;，。]+)?\b", "状态检查", text, flags=re.I)
    text = re.sub(
        r"local action pressure after\s+log_scan:([^\s;，。]+)",
        lambda match: _log_scan_label(match.group(1), suffix="的行动残留"),
        text,
        flags=re.I,
    )
    text = re.sub(
        r"\blog_scan:([^\s;，。]+)",
        lambda match: _log_scan_label(match.group(1), suffix=""),
        text,
        flags=re.I,
    )
    replacements = (
        (r"reflection queue strong topic:\s*", "反思队列："),
        (r"action residue after\s+", "行动残留来自"),
        (r"\bpressure=medium\b", "中负载"),
        (r"\bpressure=high\b", "高负载"),
        (r"\bpressure=low\b", "低负载"),
        (r"\bended as failure\b", "执行失败"),
        (r"\bended as success\b", "已完成"),
        (r"\bended as timeout\b", "执行超时"),
        (r"\bended as timed_out\b", "执行超时"),
        (r"\bended as blocked_by_boundary\b", "边界拦住"),
        (r"\bended as blocked\b", "边界拦住"),
        (r"\bended as unknown\b", "结果未知"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.I)
    return text


def visible_action_result_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    return RESULT_LABELS.get(text, text or RESULT_LABELS["unknown"])


def visible_action_pressure_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    return PRESSURE_LABELS.get(text, text or PRESSURE_LABELS["unknown"])


def visible_action_theme_label(value: Any) -> str:
    text = sanitize_visible_text(value).strip()
    lowered = text.lower()
    if "codex 委派" in lowered or "codex 委派" in text.lower():
        return "Codex 委派"
    if "状态检查" in text:
        return "状态检查"
    log_match = re.search(r"([A-Za-z0-9_.-]+)\s+日志扫描", text)
    if log_match:
        return _compact(f"{log_match.group(1)} 日志扫描", 32)
    if "日志扫描" in text:
        return "日志扫描"
    if "行动残留" in text or "本地行动" in text:
        return "本地行动"
    return _compact(text or "行动经验", 32)


def _log_scan_label(target: str, *, suffix: str) -> str:
    normalized = (target or "").strip()
    if normalized and normalized != "none":
        return f"{normalized} 日志扫描{suffix}"
    return f"日志扫描{suffix}"


def _sanitize_tool_artifacts(text: str) -> str:
    if not visible_text_has_tool_artifact(text):
        return text
    cleaned = text
    cleaned = cleaned.replace(TOOL_ARTIFACT_VISIBLE_LABEL, "")
    cleaned = re.sub(
        r"owner 留下了一次有轻微留痕意义的互动：\s*\[Tool batch completed\][^\r\n。]*",
        "",
        cleaned,
        flags=re.I,
    )
    for pattern in TOOL_ARTIFACT_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"\s+([,，;；。])", r"\1", cleaned)
    cleaned = re.sub(r"([;；,，])\s*([;；,，])+", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned


def _compact(text: str, limit: int) -> str:
    compacted = re.sub(r"\s+", " ", text).strip()
    if len(compacted) <= limit:
        return compacted
    return compacted[: max(0, limit - 3)].rstrip() + "..."
