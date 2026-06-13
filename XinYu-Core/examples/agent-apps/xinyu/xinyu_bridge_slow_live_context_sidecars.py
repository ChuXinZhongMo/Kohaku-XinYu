from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from xinyu_bridge_slow_live_state import SlowLiveResponseState


def observe_slow_live_persona_sidecar(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    observer: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    try:
        return observer(runtime.xinyu_dir, payload, text=text)
    except Exception as exc:
        print(f"[xinyu_core_bridge] persona state sidecar failed: {exc}", flush=True)
        return {
            "notes": [f"persona_state_error:{type(exc).__name__}"],
            "prompt_block": "",
        }


def run_slow_live_emotion_council_shadow(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    checked_at: str | None,
    runner: Callable[..., dict[str, Any]],
    now_func: Callable[[], datetime] | None,
) -> dict[str, Any]:
    try:
        observed_at = checked_at or (now_func() if now_func else datetime.now().astimezone()).isoformat()
        return runner(
            runtime.xinyu_dir,
            text=text,
            payload=payload,
            checked_at=observed_at,
            trigger="live_turn",
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] emotion council shadow failed: {exc}", flush=True)
        return {"notes": [f"emotion_council_error:{type(exc).__name__}"]}


def build_slow_live_response_state(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    visible_turn: Any,
    recalled_context: Any,
    evaluated_at: str,
    response_classifier: Callable[..., Any],
    scene_builder: Callable[..., Any],
    slow_state_builder: Callable[..., Any],
    safe_str_func: Callable[..., str],
) -> SlowLiveResponseState:
    try:
        response_error_decision = response_classifier(
            runtime.xinyu_dir,
            user_text=user_text,
            current_candidate_reply=reply,
            payload=payload,
            visible_turn=visible_turn,
        )
        response_error_loop = {
            "notes": [
                "response_error_loop:"
                f"{response_error_decision.error_class}/{response_error_decision.severity}"
            ]
        }
        response_scene_frame = scene_builder(
            runtime.xinyu_dir,
            user_text=user_text,
            visible_turn=visible_turn,
            canonical_recall_context=safe_str_func(getattr(recalled_context, "prompt_block", "")),
            evaluated_at=evaluated_at,
        )
        slow_state = slow_state_builder(
            runtime.xinyu_dir,
            user_text=user_text,
            scene_frame=response_scene_frame,
            response_error_decision=response_error_decision,
            evaluated_at=evaluated_at,
            persist=True,
        )
        slow_state_runtime = {
            "notes": [
                "slow_state:"
                f"{slow_state.reply_policy}/{slow_state.initiative_policy}/"
                f"{','.join(slow_state.active_policies) or 'steady'}"
            ]
        }
        return SlowLiveResponseState(
            response_error_loop=response_error_loop,
            slow_state_runtime=slow_state_runtime,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] response error/slow state failed: {exc}", flush=True)
        return SlowLiveResponseState(
            response_error_loop={"notes": [f"response_error_loop_error:{type(exc).__name__}"]},
            slow_state_runtime={"notes": [f"slow_state_error:{type(exc).__name__}"]},
        )
