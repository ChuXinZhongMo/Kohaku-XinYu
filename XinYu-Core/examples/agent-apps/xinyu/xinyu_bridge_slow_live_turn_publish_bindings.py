from __future__ import annotations

from typing import Any, Mapping


async def publish_slow_live_failed_turn_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> int:
    return await deps["_runtime_publish_slow_live_failed_turn"](
        values["runtime"],
        values["payload"],
        session=values["session"],
        text=values["text"],
        session_key=values["session_key"],
        turn_id=values["turn_id"],
        turn_started_wall=values["turn_started_wall"],
        turn_started_at=values["turn_started_at"],
        status=values["status"],
        notes=values["notes"],
        recalled_context_event=values["recalled_context_event"],
        recalled_context=values["recalled_context"],
        clock_func=deps["time"].perf_counter,
        record_finished_func=deps["record_turn_finished"],
        timestamp_func=deps["timestamp_or_now_iso"],
        safe_str_func=deps["_safe_str"],
    )


async def publish_slow_live_success_turn_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_publish_slow_live_success_turn"](
        values["runtime"],
        values["payload"],
        text=values["text"],
        reply=values["reply"],
        session_key=values["session_key"],
        turn_id=values["turn_id"],
        turn_started_wall=values["turn_started_wall"],
        turn_started_at=values["turn_started_at"],
        before_memory=values["before_memory"],
        after_memory=values["after_memory"],
        notes=values["notes"],
        archive_result=values["archive_result"],
        recalled_context_event=values["recalled_context_event"],
        recalled_context=values["recalled_context"],
        reply_bubble_force_units=values["reply_bubble_force_units"],
        trace_route_stage=values["trace_route_stage"],
        clock_func=deps["time"].perf_counter,
        record_finished_func=deps["record_turn_finished"],
        visible_text_hash_func=deps["visible_text_hash"],
        timestamp_func=deps["timestamp_or_now_iso"],
        safe_str_func=deps["_safe_str"],
    )


def notes_from_sidecar_runtime(sidecar: dict[str, Any], limit: int, deps: Mapping[str, Any]) -> list[str]:
    return deps["_runtime_notes_from_sidecar"](sidecar, limit, safe_str_func=deps["_safe_str"])


def build_slow_live_success_notes_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> list[str]:
    passthrough = {
        key: values[key]
        for key in (
            "reply",
            "empty_visible_reply_no_fallback",
            "rendered",
            "renderer_reason",
            "outward_renderer",
            "renderer_mode",
            "final_guard_flags",
            "final_guard_applied",
            "stale_context_reply_replaced",
            "visible_dedupe",
            "finish_sidecars",
            "proactive_tail_synced",
            "model_codex_delegate_note",
            "wait_to_think_task",
            "curiosity_eval",
            "private_thought_outcome",
            "uncertainty_pause_reply",
            "continuity_handoff",
            "life_reply_policy",
            "life_reply_adjustment",
            "response_error_loop",
            "slow_state_runtime",
            "current_sticker_reply",
            "recent_sticker_reply",
            "reply_bubble_force_units",
            "persona_sidecar",
            "event_sidecar",
            "v1_shadow",
            "tinykernel_shadow",
            "emotion_council",
            "recalled_context_notes",
            "expression_learning",
            "cleanup",
            "session",
        )
    }
    return deps["_runtime_build_slow_live_success_notes"](
        **passthrough,
        notes_from_sidecar_func=deps["_notes_from_sidecar"],
        safe_str_func=deps["_safe_str"],
    )
