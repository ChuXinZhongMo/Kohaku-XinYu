from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from xinyu_bridge_slow_live_state import SlowLiveModelContexts


async def build_slow_live_model_contexts(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    visible_turn: Any,
    recalled_context: Any,
    evaluated_at: str,
    continuity_refresher: Callable[..., dict[str, Any]],
    runtime_presence_builder: Callable[..., str],
    emotion_prompt_builder: Callable[..., str],
    now_func: Callable[[], datetime] | None,
    safe_str_func: Callable[..., str],
) -> SlowLiveModelContexts:
    del payload
    continuity_handoff: dict[str, Any] = {"notes": []}
    try:
        observed_at = (now_func() if now_func else datetime.now().astimezone()).isoformat()
        continuity_handoff = continuity_refresher(
            runtime.xinyu_dir,
            user_text=user_text,
            observed_at=observed_at,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] continuity handoff failed: {exc}", flush=True)
        continuity_handoff = {"notes": [f"continuity_handoff_error:{type(exc).__name__}"]}
    runtime_presence_context = runtime_presence_builder(runtime.xinyu_dir, limit=2200)
    life_reply_policy = await runtime._build_life_reply_policy(
        user_text=user_text,
        visible_turn=visible_turn,
        canonical_recall_context=safe_str_func(getattr(recalled_context, "prompt_block", "")),
        evaluated_at=evaluated_at,
    )
    emotion_council_context = ""
    if runtime.emotion_council_prompt_enabled:
        emotion_council_context = emotion_prompt_builder(runtime.xinyu_dir)
    return SlowLiveModelContexts(
        continuity_handoff=continuity_handoff,
        runtime_presence_context=runtime_presence_context,
        life_reply_policy=life_reply_policy,
        emotion_council_context=emotion_council_context,
    )
