from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from typing import Any

from xinyu_bridge_values import safe_str as _safe_str
from xinyu_continuity_handoff import build_continuity_handoff_prompt_block
from xinyu_early_visible_segment import observe_early_visible_segment_shadow
from xinyu_life_reply_policy import build_life_reply_prompt_block
from xinyu_uncertainty_pause import build_uncertainty_pause_prompt_block


def start_early_visible_shadow(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session: Any,
    text: str,
    turn_id: str,
    visible_turn: Any,
    safe_str_func: Callable[..., str] = _safe_str,
    observe_early_visible_func: Callable[..., Any] = observe_early_visible_segment_shadow,
    create_task_func: Callable[..., asyncio.Task[Any]] = asyncio.create_task,
    get_running_loop_func: Callable[[], asyncio.AbstractEventLoop] = asyncio.get_running_loop,
) -> tuple[asyncio.Event, asyncio.Task[Any] | None]:
    stop_early_shadow = asyncio.Event()
    loop = get_running_loop_func()
    early_shadow_task: asyncio.Task[Any] | None = None
    session_chunks = getattr(session, "chunks", None)
    if isinstance(session_chunks, list):
        early_shadow_task = create_task_func(
            observe_early_visible_func(
                runtime.xinyu_dir,
                session_chunks,
                payload=payload,
                user_text=text,
                turn_id=turn_id,
                session_key=safe_str_func(getattr(session, "key", "")),
                visible_turn=visible_turn,
                started_monotonic=loop.time(),
                stop_event=stop_early_shadow,
            ),
            name=f"xinyu-early-visible-segment-shadow-{turn_id or 'turn'}",
        )
    return stop_early_shadow, early_shadow_task


async def stop_early_visible_shadow(
    stop_early_shadow: asyncio.Event,
    early_shadow_task: asyncio.Task[Any] | None,
    *,
    wait_for_func: Callable[..., Any] = asyncio.wait_for,
) -> None:
    stop_early_shadow.set()
    if early_shadow_task is not None:
        with contextlib.suppress(Exception):
            await wait_for_func(early_shadow_task, timeout=1)


def inject_slow_live_turn_context(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session: Any,
    text: str,
    turn_id: str,
    visible_turn: Any,
    persona_sidecar: dict[str, Any],
    curiosity_eval: dict[str, Any],
    recalled_context: Any,
    runtime_presence_context: str,
    life_reply_policy: dict[str, Any],
    emotion_council_context: str,
    safe_str_func: Callable[..., str] = _safe_str,
    build_continuity_func: Callable[..., str] = build_continuity_handoff_prompt_block,
    build_uncertainty_func: Callable[..., str] = build_uncertainty_pause_prompt_block,
    build_life_reply_func: Callable[..., str] = build_life_reply_prompt_block,
) -> None:
    runtime._inject_live_turn_context(
        session.agent,
        payload=payload,
        text=text,
        dialogue_tail=session.dialogue_tail,
        turn_id=turn_id,
        persona_context=safe_str_func(persona_sidecar.get("prompt_block")),
        curiosity_context=safe_str_func(curiosity_eval.get("prompt_block")),
        visible_turn=visible_turn,
        recalled_context=safe_str_func(getattr(recalled_context, "prompt_block", "")),
        runtime_presence_context=runtime_presence_context,
        continuity_context=build_continuity_func(runtime.xinyu_dir, user_text=text),
        uncertainty_pause_context=build_uncertainty_func(runtime.xinyu_dir),
        life_reply_context=build_life_reply_func(life_reply_policy),
        emotion_council_context=emotion_council_context,
    )
