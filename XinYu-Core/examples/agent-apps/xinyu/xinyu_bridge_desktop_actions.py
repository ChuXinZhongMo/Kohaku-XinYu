from __future__ import annotations

from typing import Any

from xinyu_bridge_values import compact_text
from xinyu_visible_text_sanitizer import sanitize_visible_text, visible_action_theme_label


def desktop_action_result_label(value: str) -> str:
    if value == "success":
        return "已完成"
    if value in {"failure", "error"}:
        return "执行失败"
    if value == "timeout":
        return "执行超时"
    if value in {"blocked", "blocked_by_boundary"}:
        return "边界拦住"
    if not value or value == "unknown":
        return "结果未知"
    return compact_text(value, 18)


def desktop_action_pressure_label(value: str) -> str:
    if value == "high":
        return "高负载"
    if value == "medium":
        return "中负载"
    if value == "low":
        return "低负载"
    if not value or value == "unknown":
        return "负载未知"
    return compact_text(value, 18)


def desktop_action_theme_label(value: str) -> str:
    return visible_action_theme_label(value)


def desktop_scrub_action_markers(value: Any) -> str:
    return sanitize_visible_text(value)
