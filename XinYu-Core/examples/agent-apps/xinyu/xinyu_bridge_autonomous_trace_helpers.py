from __future__ import annotations

from typing import Any


def autonomous_error_note(note_kind: str, exc: Exception) -> str:
    return f"{note_kind}_error:{type(exc).__name__}"


def autonomous_error_trace_line(note_kind: str, exc: Exception) -> str:
    return f"{note_kind}_error={exc!r}"


def append_autonomous_error(
    runtime: Any,
    notes: list[str],
    note_kind: str,
    exc: Exception,
    *,
    trace: bool = True,
) -> None:
    notes.append(autonomous_error_note(note_kind, exc))
    if trace:
        runtime._trace_autonomous(autonomous_error_trace_line(note_kind, exc))
