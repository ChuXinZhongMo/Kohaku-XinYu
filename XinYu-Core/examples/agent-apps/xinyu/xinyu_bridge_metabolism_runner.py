from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


RunDueTickets = Callable[..., dict[str, Any]]
NowIso = Callable[[], str]
EventFactory = Callable[[], Any]
WaitFor = Callable[..., Awaitable[Any]]
ToThread = Callable[..., Awaitable[Any]]


async def run_due_metabolism_once(
    runtime: Any,
    *,
    trigger: str,
    run_due_tickets: RunDueTickets,
    runner_id: str,
    now_iso: NowIso,
    to_thread: ToThread = asyncio.to_thread,
) -> dict[str, Any]:
    if runtime._closed or runtime._metabolism_in_progress:
        return {"ran": 0, "notes": ["closed_or_in_progress"]}
    runtime._metabolism_in_progress = True
    runtime._metabolism_last_started_at = now_iso()
    try:
        result = await to_thread(
            run_due_tickets,
            runtime.xinyu_dir,
            runner_id=runner_id,
            max_tickets=3,
        )
        runtime._metabolism_run_count += int(result.get("ran") or 0)
        runtime._metabolism_last_result = result
        runtime._metabolism_last_success_at = now_iso()
        runtime._metabolism_last_error = ""
        await runtime._publish_metabolism_runner_result(result, trigger=trigger)
        return result
    except Exception as exc:
        runtime._metabolism_last_error = f"{type(exc).__name__}: {exc}"
        self_choice_state = await runtime.self_choice_store.apply_event_impulse("ticket_failed")
        await runtime._desktop_publish_event(
            "metabolism_runner_failed",
            {"error": runtime._metabolism_last_error, "trigger": trigger, "selfChoiceState": self_choice_state},
            severity="error",
        )
        raise
    finally:
        runtime._metabolism_in_progress = False


async def metabolism_runner_loop(
    runtime: Any,
    *,
    event_factory: EventFactory = asyncio.Event,
    wait_for: WaitFor = asyncio.wait_for,
) -> None:
    wakeup = runtime._metabolism_wakeup_event
    if wakeup is None:
        wakeup = event_factory()
        runtime._metabolism_wakeup_event = wakeup
    while not runtime._closed:
        try:
            await runtime._run_due_metabolism_once(trigger="tick")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            runtime._metabolism_last_error = f"tick_error:{exc!r}"
            print(f"[xinyu_core_bridge] metabolism runner error: {exc!r}", flush=True)
        try:
            await wait_for(wakeup.wait(), timeout=runtime.metabolism_runner_interval_seconds)
            wakeup.clear()
            if not runtime._closed:
                await runtime._run_due_metabolism_once(trigger="wakeup")
        except asyncio.TimeoutError:
            continue


def wake_metabolism_runner(runtime: Any) -> None:
    wakeup = runtime._metabolism_wakeup_event
    if wakeup is not None:
        wakeup.set()
