from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_desktop_surface_state_store import desktop_surface_state_store_for_runtime


async def build_life_reply_policy_for_runtime_impl(
    runtime: Any,
    *,
    user_text: str,
    visible_turn: Any | None = None,
    canonical_recall_context: str = "",
    evaluated_at: Any | None = None,
    sample_environment_func: Callable[..., dict[str, Any]],
    build_entropy_state_func: Callable[..., Any],
    build_scene_frame_func: Callable[..., dict[str, Any]],
    read_recent_action_context_func: Callable[..., str],
    build_life_reply_policy_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    try:
        await runtime._ensure_self_choice_ready()
        await runtime.self_choice_store.apply_time_decay()
        self_choice_public = await runtime.self_choice_store.snapshot_public(consume_cues=False)
        proactive_items = (await runtime.desktop_proactive_inbox({})).get("items", [])
        recent_turns = desktop_surface_state_store_for_runtime(runtime).recent_turns()[-30:]
        recent_memory_events = (await runtime.desktop_memory_recent({"limit": 30})).get("items", [])
        environment = sample_environment_func(runtime.xinyu_dir)
        entropy = build_entropy_state_func(
            environment=environment,
            proactive_items=proactive_items if isinstance(proactive_items, list) else [],
            recent_turns=recent_turns,
            recent_memory_events=recent_memory_events if isinstance(recent_memory_events, list) else [],
        )
        entropy_state = entropy.model_dump(mode="json") if hasattr(entropy, "model_dump") else {}
        scene_frame = build_scene_frame_func(
            runtime.xinyu_dir,
            user_text=user_text,
            visible_turn=visible_turn,
            canonical_recall_context=canonical_recall_context,
            evaluated_at=evaluated_at,
        )
        policy = build_life_reply_policy_func(
            self_choice_public=self_choice_public,
            entropy_state=entropy_state,
            recent_action_context=read_recent_action_context_func(runtime.xinyu_dir),
            user_text=user_text,
            scene_frame=scene_frame,
        )
        policy.setdefault("notes", []).append("life_reply_policy_built")
        return policy
    except Exception as exc:
        return {
            "version": 1,
            "mode": "steady",
            "reply_pressure": "normal",
            "technical_turn": False,
            "max_sentences": 3,
            "suppress_optional_question": False,
            "reasons": [],
            "notes": [f"life_reply_policy_error:{type(exc).__name__}"],
        }
