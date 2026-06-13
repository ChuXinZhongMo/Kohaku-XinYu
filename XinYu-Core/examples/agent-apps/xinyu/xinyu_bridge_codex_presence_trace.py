from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_bridge_codex_presence_store import append_codex_background_trace

CODEX_BACKGROUND_TRACE_RELATIVE_PATH = Path("knowledge/codex_delegate_background_trace.log")
CODEX_BACKGROUND_TRACE_TEXT_LIMIT = 120


def _finished_at(finished_at: str | None) -> str:
    return finished_at or datetime.now().astimezone().isoformat()


def _notes_field(notes: list[str]) -> str:
    return ";".join(notes) or "none"


def _trace_text(text: str) -> str:
    return text[:CODEX_BACKGROUND_TRACE_TEXT_LIMIT]


def codex_delegate_background_success_trace_line(
    result: Any,
    *,
    started_at: str,
    text: str,
    handoff_notes: list[str],
    report_material_id: str,
    report_material_notes: list[str],
    action_experience_notes: list[str],
    finished_at: str | None = None,
) -> str:
    return (
        f"{_finished_at(finished_at)} ok "
        f"started_at={started_at} accepted={result.accepted} timed_out={result.timed_out} "
        f"exit={result.exit_code if result.exit_code is not None else 'timeout'} "
        f"report={result.report_path} dream_handoff={_notes_field(handoff_notes)} "
        f"report_material={report_material_id or 'none'} "
        f"report_material_notes={_notes_field(report_material_notes)} "
        f"action_experience={_notes_field(action_experience_notes)} "
        f"text={_trace_text(text)!r}\n"
    )


def codex_delegate_background_error_trace_line(
    exc: BaseException,
    *,
    started_at: str,
    text: str,
    finished_at: str | None = None,
) -> str:
    return (
        f"{_finished_at(finished_at)} error "
        f"started_at={started_at} {type(exc).__name__}: {exc} text={_trace_text(text)!r}\n"
    )


def append_codex_delegate_background_trace(memory_root: Path, line: str) -> None:
    trace_path = memory_root / CODEX_BACKGROUND_TRACE_RELATIVE_PATH
    append_codex_background_trace(trace_path, line)
