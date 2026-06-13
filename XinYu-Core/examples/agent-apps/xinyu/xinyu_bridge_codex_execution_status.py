from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

from xinyu_bridge_codex_execution_response import codex_background_scheduled_response
from xinyu_bridge_codex_presence import record_codex_delegate_presence_state
from xinyu_bridge_values import safe_str
from xinyu_codex_delegate import preview_codex_delegate_paths


CODEX_BACKGROUND_SCHEDULED_SOURCE_MARKERS = (
    "codex_delegate_background:scheduled",
    "dream_handoff_on_timeout:armed",
)


async def schedule_codex_background_delegate(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    auto_study: bool,
    preview_paths_func: Callable[..., dict[str, Any]] = preview_codex_delegate_paths,
    record_presence_state_func: Callable[..., Any] = record_codex_delegate_presence_state,
    create_task_func: Callable[..., Any] = asyncio.create_task,
    response_func: Callable[..., dict[str, Any]] = codex_background_scheduled_response,
) -> dict[str, Any]:
    paths = preview_paths_func(runtime.xinyu_dir, payload)
    record_presence_state_func(
        runtime.xinyu_dir,
        payload,
        presence_paths=paths,
        status="running",
    )
    cleanup = await runtime._cleanup_idle_sessions()
    create_task_func(
        runtime._codex_delegate_background(payload, text=text, auto_study=auto_study),
        name=f"xinyu-codex-delegate-{paths['job_id']}",
    )
    reply = runtime._codex_status_reply(
        "started",
        paths=paths,
        auto_study=auto_study,
        task_text=safe_str(payload.get("raw_owner_task")).strip() or text,
    )
    return response_func(
        paths,
        reply=reply,
        auto_study=auto_study,
        cleanup=cleanup,
        session_count=len(runtime._sessions),
    )


async def start_codex_foreground_delegate(
    runtime: Any,
    payload: dict[str, Any],
    *,
    preview_paths_func: Callable[..., dict[str, Any]] = preview_codex_delegate_paths,
    record_presence_state_func: Callable[..., Any] = record_codex_delegate_presence_state,
) -> dict[str, Any]:
    cleanup = await runtime._cleanup_idle_sessions()
    presence_paths = preview_paths_func(runtime.xinyu_dir, payload)
    record_presence_state_func(
        runtime.xinyu_dir,
        payload,
        presence_paths=presence_paths,
        status="running",
    )
    return {"cleanup": cleanup, "presence_paths": presence_paths}


def prepare_codex_background_delegate_context(
    runtime: Any,
    payload: dict[str, Any],
    *,
    started_at: str | None = None,
    preview_paths_func: Callable[..., dict[str, Any]] = preview_codex_delegate_paths,
    now_func: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    observed_at = now_func() if now_func else datetime.now().astimezone()
    return {
        "started_at": started_at or observed_at.isoformat(),
        "presence_paths": preview_paths_func(runtime.xinyu_dir, payload),
        "metadata": metadata,
        "async_resume_id": safe_str(metadata.get("async_resume_id")).strip(),
        "owner_intervention": safe_str(metadata.get("owner_intervention")).strip(),
    }
