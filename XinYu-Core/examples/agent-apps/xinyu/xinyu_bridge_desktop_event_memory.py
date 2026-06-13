from __future__ import annotations

from collections.abc import Callable
from typing import Any


SafeStrFunc = Callable[..., str]


def memory_recall_notes(result: Any, *, safe_str_func: SafeStrFunc) -> list[str]:
    notes: list[str] = []
    for note in tuple(getattr(result, "notes", ()) or ()):
        text = safe_str_func(note)
        if text:
            notes.append(text)
    return notes


def memory_recall_should_skip(notes: list[str] | tuple[str, ...]) -> bool:
    return any(note in {"retrieval_disabled", "retrieval_not_needed"} for note in notes)


def memory_recall_top_sources(
    items: list[dict[str, Any]],
    *,
    dedupe_func: Callable[[list[str]], list[str]],
    safe_str_func: SafeStrFunc,
) -> list[str]:
    sources: list[str] = []
    for item in items:
        source = safe_str_func(item.get("source"))
        if source:
            sources.append(source)
    return dedupe_func(sources)[:6]


def memory_recall_remember_item(
    event: dict[str, Any],
    event_payload: dict[str, Any],
    *,
    safe_str_func: SafeStrFunc,
) -> dict[str, Any]:
    return {
        "eventId": safe_str_func(event.get("id")),
        "ts": safe_str_func(event.get("ts")),
        **event_payload,
    }
