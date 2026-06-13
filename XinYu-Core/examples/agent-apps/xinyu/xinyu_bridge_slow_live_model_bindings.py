from __future__ import annotations

from typing import Any, Mapping


async def prepare_slow_live_post_model_reply_state_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> Any:
    return await deps["_runtime_prepare_slow_live_post_model_reply_state"](
        values["runtime"],
        values["session"],
        values["payload"],
        text=values["text"],
        session_key=values["session_key"],
        recalled_context=values["recalled_context"],
        life_reply_policy=values["life_reply_policy"],
        visible_turn=values["visible_turn"],
        evaluated_at=values["evaluated_at"],
        trace_route_stage=values["trace_route_stage"],
        clock_func=deps["time"].time,
        codex_delegate_func=deps["xinyu_bridge_codex_runtime"].apply_chat_codex_reply_delegates,
        reply_adjustment_pipeline_func=deps["apply_slow_live_reply_adjustment_pipeline"],
        response_state_builder_func=deps["build_slow_live_response_state"],
        normalize_func=deps["normalize_bridge_reply"],
    )


async def prepare_slow_live_post_model_reply_state_for_turn_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> Any:
    return await deps["_runtime_prepare_slow_live_post_model_reply_state_for_turn"](
        values["runtime"],
        values["session"],
        values["payload"],
        text=values["text"],
        session_key=values["session_key"],
        model_turn=values["model_turn"],
        evaluated_at=values["evaluated_at"],
        trace_route_stage=values["trace_route_stage"],
        prepare_func=deps["prepare_slow_live_post_model_reply_state"],
    )


async def inject_slow_live_model_event_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> None:
    await deps["_runtime_inject_slow_live_model_event"](
        values["runtime"],
        values["payload"],
        session=values["session"],
        event=values["event"],
        text=values["text"],
        turn_id=values["turn_id"],
        visible_turn=values["visible_turn"],
        persona_sidecar=values["persona_sidecar"],
        curiosity_eval=values["curiosity_eval"],
        recalled_context=values["recalled_context"],
        runtime_presence_context=values["runtime_presence_context"],
        life_reply_policy=values["life_reply_policy"],
        emotion_council_context=values["emotion_council_context"],
        trace_route_stage=values["trace_route_stage"],
        safe_str_func=deps["_safe_str"],
        int_or_zero_func=deps["_int_or_zero"],
        session_output_notes_func=deps["_session_output_notes"],
        has_visible_chunks_func=deps["_has_visible_chunks"],
        owner_private_payload_matches_func=deps["_owner_private_payload_matches"],
        create_retry_event_func=deps["_create_empty_visible_retry_event"],
        build_continuity_func=deps["build_continuity_handoff_prompt_block"],
        build_uncertainty_func=deps["build_uncertainty_pause_prompt_block"],
        build_life_reply_func=deps["build_life_reply_prompt_block"],
        observe_early_visible_func=deps["observe_early_visible_segment_shadow"],
        empty_visible_retry_timeout_seconds=deps["EMPTY_VISIBLE_RETRY_TIMEOUT_SECONDS"],
        create_task_func=deps["asyncio"].create_task,
        wait_for_func=deps["asyncio"].wait_for,
        get_running_loop_func=deps["asyncio"].get_running_loop,
    )


async def run_slow_live_model_turn_with_failure_publish_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> Any:
    return await deps["_runtime_run_slow_live_model_turn_with_failure_publish"](
        values["runtime"],
        values["payload"],
        session=values["session"],
        text=values["text"],
        session_key=values["session_key"],
        turn_id=values["turn_id"],
        llm_failover_turn_id=values["llm_failover_turn_id"],
        turn_started_wall=values["turn_started_wall"],
        turn_started_at=values["turn_started_at"],
        turn_event_timestamp=values["turn_event_timestamp"],
        evaluated_at=values["evaluated_at"],
        curiosity_eval=values["curiosity_eval"],
        trace_route_stage=values["trace_route_stage"],
        persona_observer_func=deps["observe_slow_live_persona_sidecar"],
        visible_turn_classifier_func=deps["classify_visible_turn"],
        memory_recall_func=deps["run_slow_live_memory_recall"],
        model_contexts_func=deps["build_slow_live_model_contexts"],
        model_event_inject_func=deps["inject_slow_live_model_event"],
        failure_publish_func=deps["publish_slow_live_failed_turn"],
        safe_str_func=deps["_safe_str"],
        request_error_cls=deps["BridgeRequestError"],
        gateway_timeout_status=deps["HTTPStatus"].GATEWAY_TIMEOUT,
    )
