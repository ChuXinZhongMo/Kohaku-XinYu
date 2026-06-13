from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable


def record_autonomous_failure(runtime: Any, message: str) -> None:
    runtime._autonomous_failure_count += 1
    runtime._autonomous_last_error = message
    runtime._trace_autonomous(message)
    runtime._write_autonomous_state("error")


async def ensure_autonomous_session(
    runtime: Any,
    *,
    time_func: Callable[[], float],
) -> Any:
    async with runtime._global_turn_lock:
        await runtime._cleanup_idle_sessions(preserve_keys={runtime.autonomous_maintenance_session_key})
        session = await runtime._get_session(runtime.autonomous_maintenance_session_key)
        session.last_used_at = time_func()
        runtime._trace_autonomous(f"session ready key={session.key}")
        runtime._write_autonomous_state("session_ready")
        return session


async def autonomous_maintenance_loop(
    runtime: Any,
    *,
    time_func: Callable[[], float],
    sleep_func: Callable[..., Awaitable[Any]],
) -> None:
    try:
        try:
            await runtime._ensure_autonomous_session()
        except Exception as exc:
            runtime._record_autonomous_failure(f"startup_session_error:{exc!r}")

        delay = runtime.autonomous_maintenance_initial_delay_seconds
        if delay > 0:
            runtime._autonomous_next_run_at = runtime._iso_from_timestamp(time_func() + delay)
            runtime._write_autonomous_state("waiting_initial_delay")
            await sleep_func(delay)

        while not runtime._closed and runtime.autonomous_maintenance_enabled:
            try:
                await runtime._run_autonomous_maintenance_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                runtime._record_autonomous_failure(f"run_error:{exc!r}")

            runtime._autonomous_next_run_at = runtime._iso_from_timestamp(
                time_func() + runtime.autonomous_maintenance_interval_seconds
            )
            runtime._write_autonomous_state("sleeping")
            await sleep_func(runtime.autonomous_maintenance_interval_seconds)
    except asyncio.CancelledError:
        runtime._trace_autonomous("background task cancelled")
        runtime._write_autonomous_state("cancelled")
        raise
    finally:
        runtime._autonomous_in_progress = False
        if runtime._closed:
            runtime._write_autonomous_state("closed")
