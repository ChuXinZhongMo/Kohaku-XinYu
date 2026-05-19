from __future__ import annotations

from typing import Any


PROACTIVE_SOURCE_TYPES = frozenset(
    {
        "task_done",
        "task_failed",
        "runtime_error",
        "reflection_question",
        "dream_residue",
        "style_repair",
        "owner_long_idle",
    }
)

PROACTIVE_URGENT_SOURCE_TYPES = frozenset({"task_failed", "runtime_error"})

INTERNAL_RUNTIME_ERROR_LABELS = frozenset(
    {
        "watched_source",
    }
)

DESKTOP_FOCUS_LABELS = {
    "task_failed": "\u4efb\u52a1\u9700\u8981\u67e5\u770b",
    "task_done": "\u4efb\u52a1\u6709\u7ed3\u679c",
    "runtime_error": "\u8fd0\u884c\u72b6\u6001\u63d0\u9192",
    "style_repair": "\u8bf4\u8bdd\u65b9\u5f0f\u63d0\u9192",
    "reflection_question": "\u60f3\u6cd5\u5f85\u786e\u8ba4",
    "dream_residue": "\u68a6\u5883\u6b8b\u7559",
    "owner_long_idle": "\u5b89\u9759\u7b49\u5f85",
}


def normalize_source_type(value: Any) -> str:
    source_type = str(value or "").strip().lower()
    return source_type if source_type in PROACTIVE_SOURCE_TYPES else "reflection_question"


def proactive_source_is_urgent(source_type: Any) -> bool:
    return normalize_source_type(source_type) in PROACTIVE_URGENT_SOURCE_TYPES


def desktop_focus_label(source_type: Any, intent_type: Any = "") -> str:
    source = str(source_type or "").strip().lower()
    intent = str(intent_type or "").strip().lower()
    return DESKTOP_FOCUS_LABELS.get(source) or DESKTOP_FOCUS_LABELS.get(intent) or "\u4e3b\u52a8\u63d0\u9192"


def should_surface_runtime_error(*, label: Any, detail: Any = "") -> bool:
    subsystem = str(label or "").strip().lower()
    if subsystem in INTERNAL_RUNTIME_ERROR_LABELS:
        return False
    text = f"{subsystem} {detail or ''}".lower()
    if "fetch_error_connecttimeout" in text and subsystem == "watched_source":
        return False
    return True


def should_surface_desktop_item(*, source_type: Any, intent_type: Any = "", source_ref: Any = "") -> bool:
    source = str(source_type or "").strip().lower()
    intent = str(intent_type or "").strip().lower()
    ref = str(source_ref or "").strip().lower()
    if source == "runtime_error" and any(f"runtime_program_awareness:{label}" in ref for label in INTERNAL_RUNTIME_ERROR_LABELS):
        return False
    return source in PROACTIVE_SOURCE_TYPES or intent in PROACTIVE_SOURCE_TYPES
