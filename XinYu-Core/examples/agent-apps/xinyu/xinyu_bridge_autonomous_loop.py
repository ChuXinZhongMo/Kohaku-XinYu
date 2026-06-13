from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable


def create_autonomous_maintenance_event(
    runtime: Any,
    *,
    prompt: str,
    now_iso_func: Callable[[], str],
) -> Any:
    runtime._load_runtime()
    event_cls = runtime._trigger_event_cls
    if event_cls is None:
        raise RuntimeError("TriggerEvent class is unavailable")
    return event_cls(
        type="timer",
        content=prompt,
        context={
            "trigger": "scheduler",
            "source": "xinyu_core_bridge",
            "time": now_iso_func(),
            "session_id": runtime.autonomous_maintenance_session_key,
            "autonomous": True,
        },
        stackable=False,
    )


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


async def run_autonomous_maintenance_once(
    runtime: Any,
    *,
    memory_snapshot_func: Callable[..., dict[str, Any]],
    normalize_reply_func: Callable[[str], str],
    wait_for_func: Callable[..., Awaitable[Any]],
    time_func: Callable[[], float],
    now_iso_func: Callable[[], str],
) -> dict[str, Any]:
    if runtime._closed or not runtime.autonomous_maintenance_enabled:
        return {"accepted": False, "notes": ["disabled_or_closed"]}

    async with runtime._global_turn_lock:
        cleanup = await runtime._cleanup_idle_sessions(preserve_keys={runtime.autonomous_maintenance_session_key})
        session = await runtime._get_session(runtime.autonomous_maintenance_session_key)
        before_memory = memory_snapshot_func(runtime.memory_root)
        session.chunks.clear()
        event = runtime._create_autonomous_maintenance_event()
        runtime._autonomous_in_progress = True
        runtime._autonomous_last_started_at = now_iso_func()
        runtime._autonomous_last_error = ""
        runtime._trace_autonomous("run started")
        runtime._write_autonomous_state("running")

        try:
            await wait_for_func(
                session.agent.inject_event(event),
                timeout=runtime.turn_timeout_seconds,
            )
        except TimeoutError:
            try:
                session.agent.interrupt()
            except Exception:
                pass
            raise
        finally:
            runtime._autonomous_in_progress = False

        session.last_used_at = time_func()
        reply_preview = normalize_reply_func("".join(session.chunks))[:200]
        sidecar_notes = runtime._run_autonomous_self_thought_sidecars(checked_at=now_iso_func())
        after_memory = memory_snapshot_func(runtime.memory_root)
        memory_changed = before_memory != after_memory
        runtime._autonomous_run_count += 1
        runtime._autonomous_last_success_at = now_iso_func()
        notes = ["autonomous_maintenance_turn", "no_visible_reply"]
        notes.extend(sidecar_notes)
        if cleanup["cleaned_sessions"]:
            notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
        runtime._trace_autonomous(f"run finished memory_changed={memory_changed} reply_preview={reply_preview!r}")
        runtime._write_autonomous_state("last_run_ok", memory_changed=memory_changed, notes=notes)
        return {
            "accepted": True,
            "memory_changed": memory_changed,
            "reply_preview": reply_preview,
            "sessions": len(runtime._sessions),
            "notes": notes,
        }
