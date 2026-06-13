from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


def codex_completion_summary_runtime(
    runtime: Any,
    result: Any,
    *,
    limit: int,
    deps: Mapping[str, Any],
) -> str:
    return deps["_runtime_codex_completion_summary"](
        runtime,
        result,
        limit=limit,
        summary_func=deps["_codex_completion_summary"],
    )


def codex_completion_outbox_message_runtime(
    runtime: Any,
    result: Any,
    *,
    text: str,
    auto_study: bool,
    handoff_notes: list[str],
    deps: Mapping[str, Any],
) -> str:
    return deps["_runtime_codex_completion_outbox_message"](
        runtime,
        result,
        text=text,
        auto_study=auto_study,
        handoff_notes=handoff_notes,
        message_func=deps["_codex_completion_outbox_message"],
    )


def enqueue_codex_completion_if_needed_runtime(
    runtime: Any,
    payload: dict[str, Any],
    *,
    result: Any | None,
    text: str,
    auto_study: bool,
    handoff_notes: list[str],
    error: str,
    deps: Mapping[str, Any],
) -> None:
    deps["_runtime_enqueue_codex_completion_if_needed"](
        runtime,
        payload,
        result=result,
        text=text,
        auto_study=auto_study,
        handoff_notes=handoff_notes,
        error=error,
        enqueue_func=deps["_enqueue_codex_completion_if_needed"],
    )


def codex_generated_image_artifacts_runtime(
    runtime: Any,
    result: Any | None,
    *,
    task_text: str,
    limit: int,
    deps: Mapping[str, Any],
) -> list[Path]:
    return deps["_runtime_codex_generated_image_artifacts"](
        runtime,
        result,
        task_text=task_text,
        limit=limit,
        image_func=deps["_codex_generated_image_artifacts"],
    )
