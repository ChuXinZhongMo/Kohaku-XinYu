from __future__ import annotations

from typing import Any, Mapping



async def runtime_codex_delegate_background_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> None:
    await deps["_runtime_codex_delegate_background"](
        values["runtime"],
        values["payload"],
        text=values["text"],
        auto_study=values["auto_study"],
        success_trace_func=deps["codex_delegate_background_success_trace_line"],
        error_trace_func=deps["codex_delegate_background_error_trace_line"],
    )


async def stage_codex_report_material_after_delegate_runtime(
    runtime: Any,
    *,
    result: Any,
    text: str,
    job_id: str,
    auto_study: bool,
    followup_task_name: str | None,
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_stage_codex_report_material_after_delegate"](
        runtime,
        result=result,
        text=text,
        job_id=job_id,
        auto_study=auto_study,
        followup_task_name=followup_task_name,
        stage_func=deps["stage_codex_report_material"],
        create_task_func=deps["asyncio"].create_task,
        to_thread_func=deps["asyncio"].to_thread,
    )


async def handoff_codex_delegate_to_dream_runtime(
    runtime: Any,
    *,
    result: Any,
    text: str,
    use_global_turn_lock: bool,
    contain_errors: bool,
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_handoff_codex_delegate_to_dream"](
        runtime,
        result=result,
        text=text,
        use_global_turn_lock=use_global_turn_lock,
        contain_errors=contain_errors,
        handoff_func=deps["handoff_codex_to_dream"],
        to_thread_func=deps["asyncio"].to_thread,
    )


async def settle_codex_delegate_action_experience_runtime(
    runtime: Any,
    payload: dict[str, Any],
    *,
    metadata: dict[str, Any],
    result: Any,
    deps: Mapping[str, Any],
) -> list[str]:
    return await deps["_runtime_settle_codex_delegate_action_experience"](
        runtime,
        payload,
        metadata=metadata,
        result=result,
        action_outcome_func=deps["codex_delegate_action_outcome"],
    )


async def finalize_codex_foreground_delegate_response_runtime(
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
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_finalize_codex_foreground_delegate_response"](
        runtime,
        payload,
        result=result,
        text=text,
        auto_study=auto_study,
        cleanup=cleanup,
        before_memory=before_memory,
        after_memory=after_memory,
        presence_paths=presence_paths,
        status_func=deps["codex_foreground_result_status"],
        notes_func=deps["codex_foreground_result_notes"],
        response_func=deps["codex_foreground_result_response"],
    )
