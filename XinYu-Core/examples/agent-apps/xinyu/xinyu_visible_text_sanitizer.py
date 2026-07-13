from __future__ import annotations

import re
from typing import Any

from xinyu_visible_persona_voice import naturalize_internal_visible_text


RESULT_LABELS = {
    "success": "我做完了",
    "failure": "我没做成",
    "failed": "我没做成",
    "timeout": "我等不到结果",
    "timed_out": "我等不到结果",
    "blocked_by_boundary": "边界把我拦住了",
    "blocked": "边界把我拦住了",
    "unknown": "我还不确定",
}

PRESSURE_LABELS = {
    "low": "很轻",
    "medium": "有点压着",
    "high": "压得比较重",
    "unknown": "我还摸不准",
}

TOOL_ARTIFACT_VISIBLE_LABEL = "我忽略了一段工具输出"

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

INTERNAL_PROMPT_LEAK_MARKERS = (
    "<think",
    "</think",
    "/think",
    "resource_posture",
    "protected class",
    "safety ban",
    "hidden_gate",
    "prompt_hash",
    "reply_hash",
    "source_hash",
    "calibration_gate",
    "shadow_gate",
)

_INTERNAL_AFFECTIVE_TOKEN_RE = re.compile(r"\[(?:FACE|EMOTION|MOOD)_[A-Z0-9_]+\]", re.IGNORECASE)

INTERNAL_PROMPT_LEAK_PATTERNS = (
    re.compile(r"(?is)<\s*think\s*>.*?<\s*/\s*think\s*>"),
    re.compile(r"(?i)</?\s*think\s*/?\s*>"),
    re.compile(r"(?i)(?:^|\s)/think\??(?:\s|$)"),
    re.compile(r"(?i)\bIt\s+is\s+not\s+a\s+safety\s+ban\s+on\s+any\s+protected\s+class\.?\s*"),
    re.compile(
        r"(?i)-?\s*If\s+`?resource_posture`?\s+is\s+`?normal`?\s*,\s*"
        r"treat\s+it\s+as\s+ordinary\s+chat\.?\s*"
    ),
    re.compile(r"(?im)^\s*\[internal control[^\r\n]*(?:\r?\n|$)"),
    re.compile(r"(?im)^\s*hidden_[A-Za-z0-9_:-]+[^\r\n]*(?:\r?\n|$)"),
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


def visible_text_has_internal_prompt_leak(value: Any) -> bool:
    text = "" if value is None else str(value)
    if not text:
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in INTERNAL_PROMPT_LEAK_MARKERS)


def strip_internal_affective_tokens(text: str) -> str:
    if not text:
        return ""
    cleaned = _INTERNAL_AFFECTIVE_TOKEN_RE.sub("", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def sanitize_visible_text(value: Any) -> str:
    text = "" if value is None else str(value)
    if not text:
        return ""
    text = _sanitize_internal_prompt_leaks(text)
    text = _sanitize_tool_artifacts(text)
    text = strip_internal_affective_tokens(text)
    return naturalize_internal_visible_text(text)


def visible_action_result_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    return RESULT_LABELS.get(text, text or RESULT_LABELS["unknown"])


def visible_action_pressure_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    return PRESSURE_LABELS.get(text, text or PRESSURE_LABELS["unknown"])


def visible_action_theme_label(value: Any) -> str:
    text = sanitize_visible_text(value).strip()
    lowered = text.lower()
    if "我让 codex 帮忙" in lowered:
        return "我让 Codex 帮忙那次"
    if "状态检查" in text:
        return "状态检查那次"
    log_match = re.search(r"([A-Za-z0-9_.-]+)\s+的日志扫过", text)
    if log_match:
        return _compact(f"我看过 {log_match.group(1)} 日志那次", 32)
    normalized_log_match = re.search(r"([A-Za-z0-9_.-]+)\s+日志", text)
    if normalized_log_match:
        return _compact(f"我看过 {normalized_log_match.group(1)} 日志那次", 32)
    if "日志" in text:
        return "我看日志那次"
    if "动作留下" in text or "压力" in text or "本地行动" in text:
        return "本地动作留下的东西"
    return _compact(text or "行动经验", 32)


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


def _sanitize_internal_prompt_leaks(text: str) -> str:
    if not visible_text_has_internal_prompt_leak(text):
        return text
    cleaned = text
    for pattern in INTERNAL_PROMPT_LEAK_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    kept_lines: list[str] = []
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        if any(
            marker in lowered
            for marker in (
                "resource_posture",
                "protected class",
                "safety ban",
                "hidden_gate",
                "prompt_hash",
                "reply_hash",
                "source_hash",
                "calibration_gate",
                "shadow_gate",
            )
        ):
            continue
        kept_lines.append(raw_line)
    cleaned = "\n".join(kept_lines)
    cleaned = re.sub(r"[ \t]+([,.;:!?\u3002\uff0c\uff1b\uff1a])", r"\1", cleaned)
    cleaned = re.sub(r"([,.;:!?\u3002\uff0c\uff1b\uff1a])(?:\s*\1)+", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _compact(text: str, limit: int) -> str:
    compacted = re.sub(r"\s+", " ", text).strip()
    if len(compacted) <= limit:
        return compacted
    return compacted[: max(0, limit - 3)].rstrip() + "..."
