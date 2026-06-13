from __future__ import annotations

from pathlib import Path
from typing import Any

from xinyu_codex_service import codex_completion_outbox_message as _codex_completion_outbox_message
from xinyu_codex_service import codex_completion_summary as _codex_completion_summary
from xinyu_codex_service import codex_generated_image_artifacts as _codex_generated_image_artifacts
from xinyu_codex_service import enqueue_codex_completion_if_needed as _enqueue_codex_completion_if_needed


def codex_completion_summary(
    runtime: Any,
    result: Any,
    *,
    limit: int = 220,
    summary_func: Any = _codex_completion_summary,
) -> str:
    return summary_func(runtime.xinyu_dir, result, limit=limit)


def codex_completion_outbox_message(
    runtime: Any,
    result: Any,
    *,
    text: str,
    auto_study: bool,
    handoff_notes: list[str],
    message_func: Any = _codex_completion_outbox_message,
) -> str:
    return message_func(
        runtime.xinyu_dir,
        result,
        text=text,
        auto_study=auto_study,
        handoff_notes=handoff_notes,
    )


def enqueue_codex_completion_if_needed(
    runtime: Any,
    payload: dict[str, Any],
    *,
    result: Any | None,
    text: str,
    auto_study: bool,
    handoff_notes: list[str],
    error: str = "",
    enqueue_func: Any = _enqueue_codex_completion_if_needed,
) -> None:
    enqueue_func(
        runtime.xinyu_dir,
        payload,
        result=result,
        text=text,
        auto_study=auto_study,
        handoff_notes=handoff_notes,
        error=error,
    )


def codex_generated_image_artifacts(
    runtime: Any,
    result: Any | None,
    *,
    task_text: str,
    limit: int = 3,
    image_func: Any = _codex_generated_image_artifacts,
) -> list[Path]:
    return image_func(runtime.xinyu_dir, result, task_text=task_text, limit=limit)
