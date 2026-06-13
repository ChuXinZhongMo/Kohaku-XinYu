from __future__ import annotations

from typing import Any, Mapping


async def run_codex_foreground_delegate_runtime(
    runtime: Any,
    payload: dict[str, Any],
    *,
    presence_paths: dict[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_run_codex_foreground_delegate"](
        runtime,
        payload,
        presence_paths=presence_paths,
        memory_snapshot_func=deps["memory_snapshot"],
        run_delegate_func=deps["run_codex_delegate"],
        record_presence_state_func=deps["record_codex_delegate_presence_state"],
        to_thread_func=deps["asyncio"].to_thread,
    )


async def run_codex_background_delegate_runtime(
    runtime: Any,
    payload: dict[str, Any],
    *,
    deps: Mapping[str, Any],
) -> Any:
    return await deps["_runtime_run_codex_background_delegate"](
        runtime,
        payload,
        run_delegate_func=deps["run_codex_delegate"],
        to_thread_func=deps["asyncio"].to_thread,
    )
