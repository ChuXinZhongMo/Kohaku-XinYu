from __future__ import annotations

from typing import Any, Callable


def followup_row(followup: dict[str, Any]) -> dict[str, Any]:
    row = followup.get("row")
    return row if isinstance(row, dict) else {}


def followup_status_notes(
    followup: dict[str, Any],
    row: dict[str, Any],
    *,
    intercept_note: str,
    row_note_func: Callable[[dict[str, Any], Callable[..., str]], str],
    event_sidecar: dict[str, Any],
    cleanup: dict[str, Any],
    guard_flags: list[str] | tuple[str, ...],
    safe_str_func: Callable[..., str],
    extend_common_finish_notes_func: Callable[..., None],
) -> list[str]:
    notes: list[str] = [intercept_note]
    notes.extend(safe_str_func(note) for note in followup.get("notes", [])[:5])
    row_note = row_note_func(row, safe_str_func)
    if row_note:
        notes.append(row_note)
    extend_common_finish_notes_func(
        notes,
        event_sidecar=event_sidecar,
        cleanup=cleanup,
        guard_flags=guard_flags,
        safe_str_func=safe_str_func,
    )
    return notes
