from __future__ import annotations

from typing import Any, Mapping


def codex_background_scheduled_response_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return deps["_runtime_codex_background_scheduled_response"](
        values["paths"],
        reply=values["reply"],
        auto_study=values["auto_study"],
        cleanup=values["cleanup"],
        session_count=values["session_count"],
    )


async def schedule_codex_background_delegate_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_schedule_codex_background_delegate"](
        values["runtime"],
        values["payload"],
        text=values["text"],
        auto_study=values["auto_study"],
        preview_paths_func=deps["preview_codex_delegate_paths"],
        record_presence_state_func=deps["record_codex_delegate_presence_state"],
        create_task_func=deps["asyncio"].create_task,
        response_func=deps["codex_background_scheduled_response"],
    )


async def start_codex_foreground_delegate_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_start_codex_foreground_delegate"](
        values["runtime"],
        values["payload"],
        preview_paths_func=deps["preview_codex_delegate_paths"],
        record_presence_state_func=deps["record_codex_delegate_presence_state"],
    )


def prepare_codex_background_delegate_context_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return deps["_runtime_prepare_codex_background_delegate_context"](
        values["runtime"],
        values["payload"],
        started_at=values["started_at"],
        preview_paths_func=deps["preview_codex_delegate_paths"],
    )


def prepare_codex_execute_payload_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, bool]:
    return deps["_runtime_prepare_codex_execute_payload"](
        values["payload"],
        text=values["text"],
        should_auto_study=values["should_auto_study"],
        observed_at=values["observed_at"],
        timeout_seconds=values["timeout_seconds"],
        window_title=values["window_title"],
    )


async def runtime_codex_execute_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_codex_execute"](
        values["runtime"],
        values["payload"],
        should_auto_study=values["should_auto_study"],
        looks_like_codex_request_func=deps["looks_like_codex_request"],
        prepare_payload_func=deps["prepare_codex_execute_payload"],
        ambiguous_request_message=deps["CODEX_AMBIGUOUS_REQUEST_MESSAGE"],
    )
