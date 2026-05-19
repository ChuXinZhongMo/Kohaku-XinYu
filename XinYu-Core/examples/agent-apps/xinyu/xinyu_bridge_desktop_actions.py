from __future__ import annotations

from typing import Any

from xinyu_bridge_values import compact_text
from xinyu_visible_text_sanitizer import (
    sanitize_visible_text,
    visible_action_pressure_label,
    visible_action_result_label,
    visible_action_theme_label,
)


def desktop_action_result_label(value: str) -> str:
    if value == "error":
        return visible_action_result_label("failure")
    if value in {"success", "failure", "failed", "timeout", "timed_out", "blocked", "blocked_by_boundary", "unknown", ""}:
        return visible_action_result_label(value)
    return compact_text(value, 18)


def desktop_action_pressure_label(value: str) -> str:
    if value in {"high", "medium", "low", "unknown", ""}:
        return visible_action_pressure_label(value)
    return compact_text(value, 18)


def desktop_action_theme_label(value: str) -> str:
    return visible_action_theme_label(value)


def desktop_scrub_action_markers(value: Any) -> str:
    return sanitize_visible_text(value)
