from __future__ import annotations

from collections.abc import Callable
from typing import Any


async def runtime_codex_delegate_background(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    auto_study: bool,
    success_trace_func: Callable[..., str],
    error_trace_func: Callable[..., str],
    handoff_note_summary_func: Callable[[dict[str, Any]], tuple[list[str], str]],
    report_material_id_and_notes_func: Callable[[dict[str, Any]], tuple[str, list[str]]],
) -> None:
    delegate_context = runtime._prepare_codex_background_delegate_context(payload)
    started_at = delegate_context["started_at"]
    presence_paths = delegate_context["presence_paths"]
    metadata = delegate_context["metadata"]
    async_resume_id = delegate_context["async_resume_id"]
    owner_intervention = delegate_context["owner_intervention"]

    try:
        result = await runtime._run_codex_background_delegate(payload)
        action_experience_notes = await runtime._settle_codex_delegate_action_experience(
            payload,
            metadata=metadata,
            result=result,
        )
        handoff = await runtime._handoff_codex_delegate_to_dream(result=result, text=text)
        handoff_notes, _ = handoff_note_summary_func(handoff)
        report_material = await runtime._stage_codex_report_material_after_delegate(
            result=result,
            text=text,
            job_id=presence_paths["job_id"],
            auto_study=auto_study,
            followup_task_name="xinyu-codex-learning-followup",
        )
        report_material_id, report_material_notes = report_material_id_and_notes_func(report_material)
        runtime._record_codex_delegate_presence_result(
            runtime.xinyu_dir,
            payload,
            result=result,
            presence_paths=presence_paths,
        )
        runtime._enqueue_codex_completion_if_needed(
            payload,
            result=result,
            text=text,
            auto_study=auto_study,
            handoff_notes=handoff_notes,
        )
        if async_resume_id:
            runtime._notify_async_exploration_codex_result(
                payload,
                async_resume_id=async_resume_id,
                owner_intervention=owner_intervention,
                result=result,
            )
        line = success_trace_func(
            result,
            started_at=started_at,
            text=text,
            handoff_notes=handoff_notes,
            report_material_id=report_material_id,
            report_material_notes=report_material_notes,
            action_experience_notes=action_experience_notes,
        )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        runtime._record_codex_delegate_presence_state(
            runtime.xinyu_dir,
            payload,
            presence_paths=presence_paths,
            status="failed",
        )
        runtime._enqueue_codex_completion_if_needed(
            payload,
            result=None,
            text=text,
            auto_study=auto_study,
            handoff_notes=[],
            error=error,
        )
        if async_resume_id:
            runtime._notify_async_exploration_codex_result(
                payload,
                async_resume_id=async_resume_id,
                owner_intervention=owner_intervention,
                error=error,
            )
        line = error_trace_func(
            exc,
            started_at=started_at,
            text=text,
        )
    runtime._append_codex_delegate_background_trace(runtime.memory_root, line)
