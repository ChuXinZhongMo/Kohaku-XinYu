from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_slow_live_state import SlowLiveMemoryRecallResult


TraceRouteStage = Callable[..., Any]
MemoryRecallRunner = Callable[..., Any]


async def run_slow_live_memory_recall(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    session: Any,
    session_key: str,
    turn_id: str,
    visible_turn: Any,
    evaluated_at: str,
    trace_route_stage: TraceRouteStage,
    recall_runner: MemoryRecallRunner,
    safe_str_func: Callable[..., str],
) -> SlowLiveMemoryRecallResult:
    recalled_context = None
    recalled_context_event: dict[str, Any] = {}
    recalled_context_notes: list[str] = []
    try:
        trace_route_stage("memory_recall_started", route="slow_live")
        recalled_algorithm = recall_runner(
            runtime.xinyu_dir,
            payload,
            user_text=user_text,
            dialogue_tail=session.dialogue_tail,
            visible_turn=visible_turn,
            evaluated_at=evaluated_at,
        )
        recalled_context = recalled_algorithm.result
        recalled_context_notes.extend(safe_str_func(note) for note in recalled_algorithm.notes[:2])
        recalled_context_notes.extend(safe_str_func(note) for note in recalled_context.notes[:3])
        recalled_context_event = await runtime._desktop_publish_memory_recall(
            payload,
            recalled_context,
            session_key=session_key,
            turn_id=turn_id,
        )
        trace_route_stage(
            "memory_recall_finished",
            route="slow_live",
            status="ok",
            notes=recalled_context_notes[:4],
        )
    except TimeoutError as exc:
        print(f"[xinyu_core_bridge] context retrieval timed out: {exc}", flush=True)
        timeout_note = f"context_retrieval_timeout:{type(exc).__name__}"
        recalled_context_notes.append(timeout_note)
        trace_route_stage(
            "memory_recall_timeout",
            route="slow_live",
            status="timeout",
            notes=[timeout_note],
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] context retrieval failed: {exc}", flush=True)
        error_note = f"context_retrieval_error:{type(exc).__name__}"
        recalled_context_notes.append(error_note)
        trace_route_stage(
            "memory_recall_error",
            route="slow_live",
            status="error",
            notes=[error_note],
        )
    return SlowLiveMemoryRecallResult(
        recalled_context=recalled_context,
        recalled_context_event=recalled_context_event,
        recalled_context_notes=recalled_context_notes,
    )
