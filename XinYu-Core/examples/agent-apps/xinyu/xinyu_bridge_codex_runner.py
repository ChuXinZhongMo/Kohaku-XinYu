from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from xinyu_bridge_codex_presence import record_codex_delegate_presence_state
from xinyu_bridge_memory_snapshot import memory_snapshot
from xinyu_codex_delegate import run_codex_delegate


async def run_codex_foreground_delegate(
    runtime: Any,
    payload: dict[str, Any],
    *,
    presence_paths: dict[str, Any],
    memory_snapshot_func: Callable[..., Any] = memory_snapshot,
    run_delegate_func: Callable[..., Any] = run_codex_delegate,
    record_presence_state_func: Callable[..., Any] = record_codex_delegate_presence_state,
    to_thread_func: Callable[..., Any] = asyncio.to_thread,
) -> dict[str, Any]:
    async with runtime._codex_delegate_lock:
        before_memory = memory_snapshot_func(runtime.memory_root)
        try:
            result = await to_thread_func(run_delegate_func, runtime.xinyu_dir, payload)
        except Exception:
            record_presence_state_func(
                runtime.xinyu_dir,
                payload,
                presence_paths=presence_paths,
                status="failed",
            )
            raise
        after_memory = memory_snapshot_func(runtime.memory_root)
    return {
        "result": result,
        "before_memory": before_memory,
        "after_memory": after_memory,
    }


async def run_codex_background_delegate(
    runtime: Any,
    payload: dict[str, Any],
    *,
    run_delegate_func: Callable[..., Any] = run_codex_delegate,
    to_thread_func: Callable[..., Any] = asyncio.to_thread,
) -> Any:
    async with runtime._codex_delegate_lock:
        return await to_thread_func(run_delegate_func, runtime.xinyu_dir, payload)
