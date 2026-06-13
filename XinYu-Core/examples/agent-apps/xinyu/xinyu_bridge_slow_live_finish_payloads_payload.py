from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from xinyu_bridge_slow_live_finish_payloads_status import prepared_finish_status


_FINISH_SIDECAR_KEYS = (
    "payload",
    "text",
    "reply",
    "draft_reply",
    "session",
    "session_key",
    "turn_id",
    "turn_started_at",
    "before_memory",
    "visible_turn",
    "final_guard_flags",
    "expression_learning",
    "recalled_context",
    "recalled_context_notes",
    "private_thought_outcome",
    "emotion_council",
    "persona_sidecar",
    "continuity_handoff",
    "wait_to_think_sidecar",
    "self_code_task",
    "direct_codex_task",
    "model_codex_task",
    "wait_to_think_task",
    "model_codex_delegate_note",
)

_SUCCESS_PUBLISH_KEYS = (
    "text",
    "reply",
    "session_key",
    "turn_started_wall",
    "turn_started_at",
    "before_memory",
    "after_memory",
    "notes",
    "archive_result",
    "recalled_context_event",
    "recalled_context",
    "reply_bubble_force_units",
    "trace_route_stage",
)


def select_kwargs(source: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: source[key] for key in keys}


def build_finish_sidecars_kwargs(source: Mapping[str, Any]) -> dict[str, Any]:
    return select_kwargs(source, _FINISH_SIDECAR_KEYS)


def build_success_publish_kwargs(source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **select_kwargs(source, _SUCCESS_PUBLISH_KEYS),
        "turn_id": source["publish_turn_id"],
    }


def build_prepared_finish_success_kwargs(source: Mapping[str, Any]) -> dict[str, Any]:
    pre_model_phase, slow_live_entry, model_turn_state, post_model_state = prepared_finish_status(source)
    return {
        "text": source["text"],
        "reply": post_model_state.reply,
        "draft_reply": post_model_state.draft_reply,
        "session": slow_live_entry["session"],
        "session_key": source["session_key"],
        "turn_id": source["turn_id"],
        "publish_turn_id": source["publish_turn_id"],
        "turn_started_wall": source["turn_started_wall"],
        "turn_started_at": source["turn_started_at"],
        "before_memory": pre_model_phase["before_memory"],
        "visible_turn": model_turn_state.visible_turn,
        "final_guard_flags": post_model_state.final_guard_flags,
        "final_guard_applied": post_model_state.final_guard_applied,
        "stale_context_reply_replaced": post_model_state.stale_context_reply_replaced,
        "expression_learning": post_model_state.expression_learning,
        "recalled_context_event": model_turn_state.recalled_context_event,
        "recalled_context": model_turn_state.recalled_context,
        "recalled_context_notes": model_turn_state.recalled_context_notes,
        "private_thought_outcome": pre_model_phase["private_thought_outcome"],
        "emotion_council": slow_live_entry["emotion_council"],
        "persona_sidecar": model_turn_state.persona_sidecar,
        "continuity_handoff": model_turn_state.continuity_handoff,
        "wait_to_think_sidecar": post_model_state.wait_to_think_sidecar,
        "self_code_task": post_model_state.self_code_task,
        "direct_codex_task": post_model_state.direct_codex_task,
        "model_codex_task": post_model_state.model_codex_task,
        "wait_to_think_task": post_model_state.wait_to_think_task,
        "model_codex_delegate_note": post_model_state.model_codex_delegate_note,
        "empty_visible_reply_no_fallback": post_model_state.empty_visible_reply_no_fallback,
        "rendered": post_model_state.rendered,
        "renderer_reason": post_model_state.renderer_reason,
        "visible_dedupe": post_model_state.visible_dedupe,
        "proactive_tail_synced": slow_live_entry["proactive_tail_synced"],
        "curiosity_eval": pre_model_phase["curiosity_eval"],
        "uncertainty_pause_reply": pre_model_phase["uncertainty_pause_reply"],
        "life_reply_policy": model_turn_state.life_reply_policy,
        "life_reply_adjustment": post_model_state.life_reply_adjustment,
        "response_error_loop": post_model_state.response_error_loop,
        "slow_state_runtime": post_model_state.slow_state_runtime,
        "current_sticker_reply": post_model_state.current_sticker_reply,
        "recent_sticker_reply": post_model_state.recent_sticker_reply,
        "reply_bubble_force_units": post_model_state.reply_bubble_force_units,
        "event_sidecar": pre_model_phase["event_sidecar"],
        "v1_shadow": pre_model_phase["v1_shadow"],
        "tinykernel_shadow": pre_model_phase["tinykernel_shadow"],
        "cleanup": source["cleanup"],
        "trace_route_stage": source["trace_route_stage"],
    }


__all__ = [
    "build_finish_sidecars_kwargs",
    "build_prepared_finish_success_kwargs",
    "build_success_publish_kwargs",
    "select_kwargs",
]
