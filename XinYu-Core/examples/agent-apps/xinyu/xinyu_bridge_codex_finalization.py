from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from xinyu_bridge_codex_async_followups import codex_delegate_action_outcome
from xinyu_bridge_codex_finalization_background import (
    runtime_codex_delegate_background as _runtime_codex_delegate_background,
)
from xinyu_bridge_codex_finalization_followups import (
    handoff_codex_delegate_to_dream as _handoff_codex_delegate_to_dream,
    settle_codex_delegate_action_experience as _settle_codex_delegate_action_experience,
)
from xinyu_bridge_codex_finalization_foreground import (
    finalize_codex_foreground_delegate_response as _finalize_codex_foreground_delegate_response,
)
from xinyu_bridge_codex_finalization_glue import (
    action_experience_dependencies,
    background_delegate_dependencies,
    dream_handoff_dependencies,
    foreground_response_dependencies,
    report_material_after_delegate_dependencies,
)
from xinyu_bridge_codex_finalization_reports import (
    codex_report_material_id_and_notes,
    codex_report_material_summary,
    stage_codex_report_material_after_delegate as _stage_codex_report_material_after_delegate,
)
from xinyu_bridge_codex_finalization_response import (
    codex_foreground_learning_defaults,
    codex_foreground_result_notes,
    codex_foreground_result_paths,
    codex_foreground_result_response,
    codex_handoff_note_summary,
    codex_note_strings,
)
from xinyu_bridge_codex_presence import (
    codex_delegate_background_error_trace_line,
    codex_delegate_background_success_trace_line,
    codex_foreground_result_status,
)
from xinyu_bridge_learning import stage_codex_report_material
from xinyu_bridge_values import safe_str
from xinyu_codex_dream_handoff import handoff_codex_to_dream


CODEX_DREAM_HANDOFF_FAILED_NOTE_PREFIX = "codex_dream_handoff_failed"


async def runtime_codex_delegate_background(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    auto_study: bool,
    success_trace_func: Callable[..., str] | None = None,
    error_trace_func: Callable[..., str] | None = None,
) -> None:
    await _runtime_codex_delegate_background(
        runtime,
        payload,
        text=text,
        auto_study=auto_study,
        **background_delegate_dependencies(
            globals(),
            success_trace_func=success_trace_func,
            error_trace_func=error_trace_func,
        ),
    )


async def stage_codex_report_material_after_delegate(
    runtime: Any,
    *,
    result: Any,
    text: str,
    job_id: str,
    auto_study: bool,
    followup_task_name: str | None = None,
    stage_func: Callable[..., dict[str, Any]] | None = None,
    create_task_func: Callable[..., Any] | None = None,
    to_thread_func: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    return await _stage_codex_report_material_after_delegate(
        runtime,
        result=result,
        text=text,
        job_id=job_id,
        auto_study=auto_study,
        followup_task_name=followup_task_name,
        **report_material_after_delegate_dependencies(
            globals(),
            stage_func=stage_func,
            create_task_func=create_task_func,
            to_thread_func=to_thread_func,
        ),
    )


async def handoff_codex_delegate_to_dream(
    runtime: Any,
    *,
    result: Any,
    text: str,
    use_global_turn_lock: bool = False,
    contain_errors: bool = False,
    handoff_func: Callable[..., Any] | None = None,
    to_thread_func: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    return await _handoff_codex_delegate_to_dream(
        runtime,
        result=result,
        text=text,
        use_global_turn_lock=use_global_turn_lock,
        contain_errors=contain_errors,
        **dream_handoff_dependencies(
            globals(),
            handoff_func=handoff_func,
            to_thread_func=to_thread_func,
        ),
    )


async def settle_codex_delegate_action_experience(
    runtime: Any,
    payload: dict[str, Any],
    *,
    metadata: dict[str, Any],
    result: Any,
    action_outcome_func: Callable[..., dict[str, Any]] | None = None,
) -> list[str]:
    return await _settle_codex_delegate_action_experience(
        runtime,
        payload,
        metadata=metadata,
        result=result,
        **action_experience_dependencies(globals(), action_outcome_func=action_outcome_func),
    )


async def finalize_codex_foreground_delegate_response(
    runtime: Any,
    payload: dict[str, Any],
    *,
    result: Any,
    text: str,
    auto_study: bool,
    cleanup: dict[str, Any],
    before_memory: Any,
    after_memory: Any,
    presence_paths: dict[str, Any],
    status_func: Callable[..., str] | None = None,
    notes_func: Callable[..., list[str]] | None = None,
    response_func: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return await _finalize_codex_foreground_delegate_response(
        runtime,
        payload,
        result=result,
        text=text,
        auto_study=auto_study,
        cleanup=cleanup,
        before_memory=before_memory,
        after_memory=after_memory,
        presence_paths=presence_paths,
        **foreground_response_dependencies(
            globals(),
            status_func=status_func,
            notes_func=notes_func,
            response_func=response_func,
        ),
    )
