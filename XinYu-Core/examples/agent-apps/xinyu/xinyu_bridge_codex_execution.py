from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

from xinyu_bridge_codex_execution_contract import (
    build_codex_execution_plan,
    ensure_codex_execution_text,
    normalize_codex_execution_payload,
)
from xinyu_bridge_codex_execution_backend import (
    CodexExecutionBackend,
    codex_execution_backend_for_runtime,
)
from xinyu_bridge_codex_execution_payload import (
    CODEX_VISIBLE_WINDOW_TITLE as _CODEX_VISIBLE_WINDOW_TITLE,
    prepare_codex_execute_payload as _prepare_codex_execute_payload,
)
from xinyu_bridge_codex_execution_response import codex_background_scheduled_response
from xinyu_bridge_codex_execution_status import (
    CODEX_BACKGROUND_SCHEDULED_SOURCE_MARKERS as _CODEX_BACKGROUND_SCHEDULED_SOURCE_MARKERS,
    prepare_codex_background_delegate_context as _prepare_codex_background_delegate_context,
    schedule_codex_background_delegate as _schedule_codex_background_delegate,
    start_codex_foreground_delegate as _start_codex_foreground_delegate,
)
from xinyu_bridge_codex_execution_timeout import CODEX_DEFAULT_TIMEOUT_SECONDS as _CODEX_DEFAULT_TIMEOUT_SECONDS
from xinyu_bridge_codex_presence import record_codex_delegate_presence_state
from xinyu_codex_delegate import looks_like_codex_request, preview_codex_delegate_paths


CODEX_DEFAULT_TIMEOUT_SECONDS = _CODEX_DEFAULT_TIMEOUT_SECONDS
CODEX_VISIBLE_WINDOW_TITLE = _CODEX_VISIBLE_WINDOW_TITLE
CODEX_AMBIGUOUS_REQUEST_MESSAGE = "这句还不像一个明确的 Codex 任务，我先不启动。你把要查或要做的主题说完整一点。"
CODEX_BACKGROUND_SCHEDULED_SOURCE_MARKERS = _CODEX_BACKGROUND_SCHEDULED_SOURCE_MARKERS
CODEX_EXECUTION_SOURCE_SMOKE_LITERALS = (
    "codex_delegate_background:scheduled",
    "dream_handoff_on_timeout:armed",
    'payload["visible_window"] = True',
    'payload["window_title"]',
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
    return await _schedule_codex_background_delegate(
        runtime,
        payload,
        text=text,
        auto_study=auto_study,
        preview_paths_func=preview_paths_func,
        record_presence_state_func=record_presence_state_func,
        create_task_func=create_task_func,
        response_func=response_func,
    )


async def start_codex_foreground_delegate(
    runtime: Any,
    payload: dict[str, Any],
    *,
    preview_paths_func: Callable[..., dict[str, Any]] = preview_codex_delegate_paths,
    record_presence_state_func: Callable[..., Any] = record_codex_delegate_presence_state,
) -> dict[str, Any]:
    return await _start_codex_foreground_delegate(
        runtime,
        payload,
        preview_paths_func=preview_paths_func,
        record_presence_state_func=record_presence_state_func,
    )


def prepare_codex_background_delegate_context(
    runtime: Any,
    payload: dict[str, Any],
    *,
    started_at: str | None = None,
    preview_paths_func: Callable[..., dict[str, Any]] = preview_codex_delegate_paths,
    now_func: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    return _prepare_codex_background_delegate_context(
        runtime,
        payload,
        started_at=started_at,
        preview_paths_func=preview_paths_func,
        now_func=now_func,
    )


def prepare_codex_execute_payload(
    payload: dict[str, Any],
    *,
    text: str,
    should_auto_study: Callable[[str], bool],
    observed_at: datetime | None = None,
    timeout_seconds: int = CODEX_DEFAULT_TIMEOUT_SECONDS,
    window_title: str = CODEX_VISIBLE_WINDOW_TITLE,
) -> dict[str, bool]:
    return _prepare_codex_execute_payload(
        payload,
        text=text,
        should_auto_study=should_auto_study,
        observed_at=observed_at,
        timeout_seconds=timeout_seconds,
        window_title=window_title,
    )


async def runtime_codex_execute(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    should_auto_study: Callable[[str], bool],
    looks_like_codex_request_func: Callable[[str], bool] = looks_like_codex_request,
    prepare_payload_func: Callable[..., dict[str, bool]] = prepare_codex_execute_payload,
    ambiguous_request_message: str = CODEX_AMBIGUOUS_REQUEST_MESSAGE,
    execution_backend: CodexExecutionBackend | None = None,
) -> dict[str, Any]:
    payload = normalize_codex_execution_payload(payload, runtime_closed=runtime._closed)
    text = runtime._payload_text(payload)
    ensure_codex_execution_text(
        text,
        looks_like_codex_request_func=looks_like_codex_request_func,
        ambiguous_request_message=ambiguous_request_message,
    )

    text = runtime._augment_codex_payload_with_dialogue_context(payload, text)
    plan = build_codex_execution_plan(
        payload,
        text=text,
        should_auto_study=should_auto_study,
        prepare_payload_func=prepare_payload_func,
    )
    backend = codex_execution_backend_for_runtime(runtime, explicit_backend=execution_backend)
    return await backend.execute(runtime, plan)
