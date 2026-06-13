from __future__ import annotations

from typing import Any, Mapping


def codex_foreground_result_response_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return deps["_runtime_codex_foreground_result_response"](
        values["result"],
        reply=values["reply"],
        memory_changed=values["memory_changed"],
        session_count=values["session_count"],
        gate=values["gate"],
        learner=values["learner"],
        quality=values["quality"],
        integrated=values["integrated"],
        ready=values["ready"],
        blocked_unreadable=values["blocked_unreadable"],
        quality_grade=values["quality_grade"],
        notes=values["notes"],
    )


def codex_foreground_result_notes_runtime(
    result: Any,
    *,
    report_material_id: str,
    report_material_notes: list[str],
    handoff_notes: list[str],
    handoff_error_note: str,
    auto_study: bool,
    cleanup: dict[str, Any],
    deps: Mapping[str, Any],
) -> list[str]:
    return deps["_runtime_codex_foreground_result_notes"](
        result,
        report_material_id=report_material_id,
        report_material_notes=report_material_notes,
        handoff_notes=handoff_notes,
        handoff_error_note=handoff_error_note,
        auto_study=auto_study,
        cleanup=cleanup,
    )
