from __future__ import annotations

from collections.abc import Callable
from typing import Any


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
    status_func: Callable[..., str],
    notes_func: Callable[..., list[str]],
    response_func: Callable[..., dict[str, Any]],
    result_paths_func: Callable[[Any], dict[str, Any]],
    learning_defaults_func: Callable[..., dict[str, Any]],
    handoff_note_summary_func: Callable[[dict[str, Any]], tuple[list[str], str]],
    report_material_id_and_notes_func: Callable[[dict[str, Any]], tuple[str, list[str]]],
    safe_str_func: Callable[[Any], str],
) -> dict[str, Any]:
    paths = result_paths_func(result)
    status = status_func(result)
    runtime._record_codex_delegate_presence_result(
        runtime.xinyu_dir,
        payload,
        result=result,
        presence_paths=presence_paths,
    )
    reply = runtime._codex_status_reply(
        status,
        paths=paths,
        auto_study=auto_study,
        exit_code=result.exit_code,
        task_text=safe_str_func(payload.get("raw_owner_task")).strip() or text,
    )
    report_material = await runtime._stage_codex_report_material_after_delegate(
        result=result,
        text=text,
        job_id=presence_paths["job_id"],
        auto_study=auto_study,
    )
    codex_report_material_id, codex_report_material_notes = report_material_id_and_notes_func(report_material)

    handoff = await runtime._handoff_codex_delegate_to_dream(
        result=result,
        text=text,
        use_global_turn_lock=True,
        contain_errors=True,
    )
    handoff_notes, handoff_error_note = handoff_note_summary_func(handoff)
    notes = notes_func(
        result,
        report_material_id=codex_report_material_id,
        report_material_notes=codex_report_material_notes,
        handoff_notes=handoff_notes,
        handoff_error_note=handoff_error_note,
        auto_study=auto_study,
        cleanup=cleanup,
    )
    learning = learning_defaults_func(result, auto_study=auto_study)

    return response_func(
        result,
        reply=reply,
        memory_changed=before_memory != after_memory or bool(codex_report_material_id),
        session_count=len(runtime._sessions),
        **learning,
        notes=notes,
    )
