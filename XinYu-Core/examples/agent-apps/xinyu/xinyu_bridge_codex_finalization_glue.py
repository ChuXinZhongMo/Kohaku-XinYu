from __future__ import annotations

from typing import Any


def _resolved(default: Any, override: Any) -> Any:
    return default if override is None else override


def background_delegate_dependencies(
    namespace: dict[str, Any],
    *,
    success_trace_func: Any,
    error_trace_func: Any,
) -> dict[str, Any]:
    return {
        "success_trace_func": _resolved(namespace["codex_delegate_background_success_trace_line"], success_trace_func),
        "error_trace_func": _resolved(namespace["codex_delegate_background_error_trace_line"], error_trace_func),
        "handoff_note_summary_func": namespace["codex_handoff_note_summary"],
        "report_material_id_and_notes_func": namespace["codex_report_material_id_and_notes"],
    }


def report_material_after_delegate_dependencies(
    namespace: dict[str, Any],
    *,
    stage_func: Any,
    create_task_func: Any,
    to_thread_func: Any,
) -> dict[str, Any]:
    asyncio_module = namespace["asyncio"]
    return {
        "stage_func": _resolved(namespace["stage_codex_report_material"], stage_func),
        "create_task_func": _resolved(asyncio_module.create_task, create_task_func),
        "to_thread_func": _resolved(asyncio_module.to_thread, to_thread_func),
    }


def dream_handoff_dependencies(
    namespace: dict[str, Any],
    *,
    handoff_func: Any,
    to_thread_func: Any,
) -> dict[str, Any]:
    return {
        "handoff_func": _resolved(namespace["handoff_codex_to_dream"], handoff_func),
        "to_thread_func": _resolved(namespace["asyncio"].to_thread, to_thread_func),
        "error_note_prefix": namespace["CODEX_DREAM_HANDOFF_FAILED_NOTE_PREFIX"],
    }


def action_experience_dependencies(
    namespace: dict[str, Any],
    *,
    action_outcome_func: Any,
) -> dict[str, Any]:
    return {
        "action_outcome_func": _resolved(namespace["codex_delegate_action_outcome"], action_outcome_func),
    }


def foreground_response_dependencies(
    namespace: dict[str, Any],
    *,
    status_func: Any,
    notes_func: Any,
    response_func: Any,
) -> dict[str, Any]:
    return {
        "status_func": _resolved(namespace["codex_foreground_result_status"], status_func),
        "notes_func": _resolved(namespace["codex_foreground_result_notes"], notes_func),
        "response_func": _resolved(namespace["codex_foreground_result_response"], response_func),
        "result_paths_func": namespace["codex_foreground_result_paths"],
        "learning_defaults_func": namespace["codex_foreground_learning_defaults"],
        "handoff_note_summary_func": namespace["codex_handoff_note_summary"],
        "report_material_id_and_notes_func": namespace["codex_report_material_id_and_notes"],
        "safe_str_func": namespace["safe_str"],
    }
