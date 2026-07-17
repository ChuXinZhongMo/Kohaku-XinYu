from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

from xinyu_bridge_heavy_maintenance import spawn_heavy_maintenance
from xinyu_bridge_memory_snapshot import memory_snapshot


def _plan_maintenance_ticks(runtime: Any) -> dict[str, Any]:
    """E4: joint priority — defer heavy work under device pressure; keep light turn."""
    root = getattr(runtime, "xinyu_dir", None) or getattr(runtime, "memory_root", None)
    try:
        from xinyu_device_resource_gate import evaluate_device_resource_gate
        from xinyu_tick_priority_queue import (
            TickCandidate,
            plan_from_device_gate,
            resource_pressure_from_device_metrics,
            should_run_kind,
        )

        device = evaluate_device_resource_gate(Path(root) if root is not None else Path("."))
        plan = plan_from_device_gate(
            [
                TickCandidate(kind="live_chat", ready=False, label="slot"),
                TickCandidate(kind="maintenance", ready=True, label="auto"),
                TickCandidate(kind="tech_scout", ready=True, label="sidecar"),
                TickCandidate(kind="proactive", ready=False, label="slot"),
            ],
            device,
            max_allowed=2,
        )
        pressure = resource_pressure_from_device_metrics(device.metrics)
        run_heavy = bool(device.allowed) and pressure < 0.85
        return {
            "device_allowed": bool(device.allowed),
            "device_reason": str(device.reason or ""),
            "pressure": pressure,
            "run_heavy": run_heavy,
            "run_maintenance_light": True,
            "allow_scout_slot": should_run_kind(plan, "tech_scout"),
            "plan": plan.as_dict(),
            "note": (
                f"tick_queue:heavy={run_heavy};scout={should_run_kind(plan, 'tech_scout')};"
                f"device={device.reason};pressure={pressure:.2f}"
            ),
        }
    except Exception as exc:
        return {
            "device_allowed": True,
            "device_reason": "gate_error",
            "pressure": 0.0,
            "run_heavy": True,
            "run_maintenance_light": True,
            "allow_scout_slot": True,
            "plan": {},
            "note": f"tick_queue:error:{type(exc).__name__}",
        }


def _refresh_nine_score_quiet(runtime: Any) -> str | None:
    root = getattr(runtime, "xinyu_dir", None)
    if root is None:
        return None
    try:
        from xinyu_nine_score import refresh_nine_scorecard
        from xinyu_nine_score_ab import run_nine_score_ab_sample

        report = refresh_nine_scorecard(Path(root), persist_reweight=None)
        overall = (report.get("scores") or {}).get("overall")
        ab = run_nine_score_ab_sample(Path(root), persist=True)
        delta = ab.get("delta_overall")
        return f"nine_score_refreshed:overall={overall};ab_delta={delta}"
    except Exception as exc:
        return f"nine_score_refresh_error:{type(exc).__name__}"


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

    tick = _plan_maintenance_ticks(runtime)
    runtime._trace_autonomous(str(tick.get("note") or "tick_queue"))

    # Run the deterministic heavy lanes in an isolated process first, off the global
    # turn lock so live chat is not blocked while they churn — unless E4 defers.
    if tick.get("run_heavy", True):
        heavy = await spawn_heavy_maintenance(runtime)
    else:
        heavy = {"status": "tick_deferred_device", "tick": tick.get("note")}
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
        if tick.get("note"):
            notes.append(str(tick["note"]))
        notes.extend(sidecar_notes)
        if cleanup["cleaned_sessions"]:
            notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
        score_note = _refresh_nine_score_quiet(runtime)
        if score_note:
            notes.append(score_note)
        runtime._trace_autonomous(f"run finished memory_changed={memory_changed} reply_preview={reply_preview!r}")
        runtime._write_autonomous_state("last_run_ok", memory_changed=memory_changed, notes=notes)
        return {
            "accepted": True,
            "memory_changed": memory_changed,
            "reply_preview": reply_preview,
            "sessions": len(runtime._sessions),
            "notes": notes,
            "tick_queue": tick,
        }
