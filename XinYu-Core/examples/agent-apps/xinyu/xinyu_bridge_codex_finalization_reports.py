from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from xinyu_bridge_codex_finalization_response import codex_nonempty_note_strings
from xinyu_bridge_learning import stage_codex_report_material
from xinyu_bridge_values import safe_str


def empty_codex_report_material() -> dict[str, Any]:
    return {"material_id": "", "notes": []}


def codex_report_material_summary(report_material: dict[str, Any]) -> dict[str, Any]:
    return {
        "material_id": safe_str(report_material.get("material_id")).strip(),
        "notes": codex_nonempty_note_strings(report_material.get("notes", []), limit=3),
    }


def codex_report_material_id_and_notes(report_material: dict[str, Any]) -> tuple[str, list[str]]:
    summary = codex_report_material_summary(report_material)
    return summary["material_id"], summary["notes"]


def schedule_codex_learning_followup(
    runtime: Any,
    *,
    create_task_func: Callable[..., Any],
    followup_task_name: str | None,
) -> None:
    followup = runtime._codex_learning_followup("codex_delegate_async")
    if followup_task_name:
        create_task_func(followup, name=followup_task_name)
    else:
        create_task_func(followup)


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
    if not result.accepted or not auto_study:
        return empty_codex_report_material()
    if stage_func is None:
        stage_func = stage_codex_report_material
    if create_task_func is None:
        create_task_func = asyncio.create_task
    if to_thread_func is None:
        to_thread_func = asyncio.to_thread
    async with runtime._global_turn_lock:
        report_material = await to_thread_func(
            stage_func,
            runtime.xinyu_dir,
            report_path=result.report_path,
            task_text=text,
            job_id=job_id,
        )
    summary = codex_report_material_summary(report_material)
    schedule_codex_learning_followup(
        runtime,
        create_task_func=create_task_func,
        followup_task_name=followup_task_name,
    )
    return summary
