from __future__ import annotations

from typing import Any, Mapping


async def run_slow_live_finish_sidecars_with_trace_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_run_slow_live_finish_sidecars_with_trace"](
        values["runtime"],
        sidecars_runner=values["sidecars_runner"],
        trace_route_stage=values["trace_route_stage"],
        **values["kwargs"],
    )


async def finish_and_publish_slow_live_success_turn_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    passthrough = {
        key: values[key]
        for key in (
            "text",
            "reply",
            "draft_reply",
            "session",
            "session_key",
            "turn_id",
            "publish_turn_id",
            "turn_started_wall",
            "turn_started_at",
            "before_memory",
            "visible_turn",
            "final_guard_flags",
            "final_guard_applied",
            "stale_context_reply_replaced",
            "expression_learning",
            "recalled_context",
            "recalled_context_event",
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
            "empty_visible_reply_no_fallback",
            "rendered",
            "renderer_reason",
            "visible_dedupe",
            "proactive_tail_synced",
            "curiosity_eval",
            "uncertainty_pause_reply",
            "life_reply_policy",
            "life_reply_adjustment",
            "response_error_loop",
            "slow_state_runtime",
            "current_sticker_reply",
            "recent_sticker_reply",
            "reply_bubble_force_units",
            "event_sidecar",
            "v1_shadow",
            "tinykernel_shadow",
            "cleanup",
            "trace_route_stage",
        )
    }
    return await deps["_runtime_finish_and_publish_slow_live_success_turn"](
        values["runtime"],
        values["payload"],
        **passthrough,
        finish_sidecars_with_trace_func=deps["run_slow_live_finish_sidecars_with_trace"],
        sidecars_runner=deps["run_slow_turn_finish_sidecars"],
        build_success_notes_func=deps["build_slow_live_success_notes"],
        publish_success_func=deps["publish_slow_live_success_turn"],
    )


async def finish_prepared_slow_live_success_turn_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_finish_prepared_slow_live_success_turn"](
        values["runtime"],
        values["payload"],
        text=values["text"],
        session_key=values["session_key"],
        turn_id=values["turn_id"],
        publish_turn_id=values["publish_turn_id"],
        turn_started_wall=values["turn_started_wall"],
        turn_started_at=values["turn_started_at"],
        pre_model_phase=values["pre_model_phase"],
        slow_live_entry=values["slow_live_entry"],
        model_turn=values["model_turn"],
        post_model_reply=values["post_model_reply"],
        cleanup=values["cleanup"],
        trace_route_stage=values["trace_route_stage"],
        finish_success_func=deps["finish_and_publish_slow_live_success_turn"],
        model_turn_coercer=deps["_coerce_model_turn_state"],
        post_model_reply_coercer=deps["_coerce_post_model_reply_state"],
    )


async def run_slow_live_turn_from_pre_model_phase_with_trace_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_run_slow_live_turn_from_pre_model_phase_with_trace"](
        values["runtime"],
        values["payload"],
        text=values["text"],
        session_key=values["session_key"],
        turn_id=values["turn_id"],
        publish_turn_id=values["publish_turn_id"],
        turn_started_wall=values["turn_started_wall"],
        turn_started_at=values["turn_started_at"],
        turn_event_timestamp=values["turn_event_timestamp"],
        turn_event_time=values["turn_event_time"],
        pre_model_phase=values["pre_model_phase"],
        cleanup=values["cleanup"],
        settle_seconds=values["settle_seconds"],
        trace_route_stage=values["trace_route_stage"],
        enter_func=deps["enter_slow_live_route_with_trace"],
        model_turn_func=deps["run_slow_live_model_turn_with_failure_publish"],
        prepare_post_model_func=deps["prepare_slow_live_post_model_reply_state_for_turn"],
        finish_prepared_func=deps["finish_prepared_slow_live_success_turn"],
        sleep_func=deps["asyncio"].sleep,
    )
