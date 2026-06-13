from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from xinyu_bridge_values import safe_str


def codex_note_strings(notes: Iterable[Any]) -> list[str]:
    return [safe_str(note) for note in notes]


def codex_handoff_note_summary(handoff: dict[str, Any]) -> tuple[list[str], str]:
    return codex_note_strings(handoff.get("notes", [])), safe_str(handoff.get("error_note"))


def codex_nonempty_note_strings(notes: Iterable[Any], *, limit: int | None = None) -> list[str]:
    cleaned: list[str] = []
    for note in notes:
        text = safe_str(note)
        if not text:
            continue
        cleaned.append(text)
        if limit is not None and len(cleaned) >= limit:
            break
    return cleaned


def codex_foreground_result_paths(result: Any) -> dict[str, Any]:
    return {
        "request_path": result.request_path,
        "workspace_path": result.workspace_path,
        "report_path": result.report_path,
        "last_message_path": result.last_message_path,
    }


def codex_foreground_learning_defaults(result: Any, *, auto_study: bool) -> dict[str, Any]:
    return {
        "gate": {},
        "learner": {},
        "quality": {},
        "integrated": 0,
        "ready": 0,
        "blocked_unreadable": 0,
        "quality_grade": "scheduled" if result.accepted and auto_study else "not_run",
    }


def codex_foreground_result_response(
    result: Any,
    *,
    reply: str,
    memory_changed: bool,
    session_count: int,
    gate: dict[str, object],
    learner: dict[str, object],
    quality: dict[str, object],
    integrated: int,
    ready: int,
    blocked_unreadable: int,
    quality_grade: str,
    notes: list[str],
) -> dict[str, Any]:
    return {
        "accepted": result.accepted,
        "reply": reply,
        "memory_changed": memory_changed,
        "library_changed": True,
        "session_created": False,
        "sessions": session_count,
        "request_path": result.request_path,
        "workspace_path": result.workspace_path,
        "report_path": result.report_path,
        "last_message_path": result.last_message_path,
        "codex_exit_code": result.exit_code,
        "codex_timed_out": result.timed_out,
        "stdout_tail": result.stdout_tail,
        "stderr_tail": result.stderr_tail,
        "source_integration_gate": gate,
        "learner_integration": learner,
        "learning_quality": quality,
        "integrated_materials": integrated,
        "ready_materials": ready,
        "blocked_unreadable_materials": blocked_unreadable,
        "quality_grade": quality_grade,
        "notes": notes,
    }


def codex_foreground_result_notes(
    result: Any,
    *,
    report_material_id: str,
    report_material_notes: list[str],
    handoff_notes: list[str],
    handoff_error_note: str,
    auto_study: bool,
    cleanup: dict[str, Any],
) -> list[str]:
    notes = list(result.notes)
    if report_material_id:
        notes.append(f"codex_report_material:{report_material_id}")
    notes.extend(report_material_notes)
    notes.extend(handoff_notes)
    if handoff_error_note:
        notes.append(handoff_error_note)
    notes.append("learning_after_codex:" + ("scheduled" if result.accepted and auto_study else "skipped"))
    if cleanup["cleaned_sessions"]:
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
    return notes
