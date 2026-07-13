from __future__ import annotations

from typing import Any, Awaitable, Callable

from xinyu_bridge_heavy_maintenance import spawn_heavy_maintenance
from xinyu_bridge_memory_snapshot import memory_snapshot


async def run_autonomous_maintenance_once(
    runtime: Any,
    *,
    normalize_reply_func: Callable[[str], str],
    wait_for_func: Callable[..., Awaitable[Any]],
    time_func: Callable[[], float],
    now_iso_func: Callable[[], str],
) -> dict[str, Any]:
    if runtime._closed or not runtime.autonomous_maintenance_enabled:
        return {"accepted": False, "notes": ["disabled_or_closed"]}

    # Run the deterministic heavy lanes in an isolated process first, off the global
    # turn lock so live chat is not blocked while they churn.
    heavy = await spawn_heavy_maintenance(runtime)
    runtime._trace_autonomous(f"heavy_maintenance {heavy.get('status')}")

    async with runtime._global_turn_lock:
        cleanup = await runtime._cleanup_idle_sessions(preserve_keys={runtime.autonomous_maintenance_session_key})
        session = await runtime._get_session(runtime.autonomous_maintenance_session_key)
        before_memory = memory_snapshot(runtime.memory_root)
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
        after_memory = memory_snapshot(runtime.memory_root)
        memory_changed = before_memory != after_memory
        runtime._autonomous_run_count += 1
        runtime._autonomous_last_success_at = now_iso_func()
        notes = ["autonomous_maintenance_turn", "no_visible_reply", f"heavy_maintenance:{heavy.get('status')}"]
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
