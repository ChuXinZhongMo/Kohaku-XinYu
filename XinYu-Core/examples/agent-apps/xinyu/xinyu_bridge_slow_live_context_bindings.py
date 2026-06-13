from __future__ import annotations

from typing import Any, Mapping


async def run_slow_live_memory_recall_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> Any:
    return await deps["_runtime_run_slow_live_memory_recall"](
        values["runtime"],
        values["payload"],
        user_text=values["user_text"],
        session=values["session"],
        session_key=values["session_key"],
        turn_id=values["turn_id"],
        visible_turn=values["visible_turn"],
        evaluated_at=values["evaluated_at"],
        trace_route_stage=values["trace_route_stage"],
        recall_runner=values["recall_runner"] or deps["run_living_memory_recall_algorithm"],
        safe_str_func=deps["_safe_str"],
    )


async def build_slow_live_model_contexts_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> Any:
    return await deps["_runtime_build_slow_live_model_contexts"](
        values["runtime"],
        values["payload"],
        user_text=values["user_text"],
        visible_turn=values["visible_turn"],
        recalled_context=values["recalled_context"],
        evaluated_at=values["evaluated_at"],
        continuity_refresher=deps["refresh_continuity_handoff"],
        runtime_presence_builder=deps["build_runtime_presence_prompt_block"],
        emotion_prompt_builder=deps["build_emotion_council_prompt_block"],
        safe_str_func=deps["_safe_str"],
    )


def observe_slow_live_persona_sidecar_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return deps["_runtime_observe_slow_live_persona_sidecar"](
        values["runtime"],
        values["payload"],
        text=values["text"],
        observer=values["observer"] or deps["observe_persona_turn"],
    )


def run_slow_live_emotion_council_shadow_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return deps["_runtime_run_slow_live_emotion_council_shadow"](
        values["runtime"],
        values["payload"],
        text=values["text"],
        checked_at=values["checked_at"],
        runner=values["runner"] or deps["run_emotion_council_shadow"],
    )


def build_slow_live_response_state_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> Any:
    return deps["_runtime_build_slow_live_response_state"](
        values["runtime"],
        values["payload"],
        user_text=values["user_text"],
        reply=values["reply"],
        visible_turn=values["visible_turn"],
        recalled_context=values["recalled_context"],
        evaluated_at=values["evaluated_at"],
        response_classifier=values["response_classifier"] or deps["classify_response_error"],
        scene_builder=values["scene_builder"] or deps["build_scene_frame"],
        slow_state_builder=values["slow_state_builder"] or deps["build_slow_state"],
        safe_str_func=deps["_safe_str"],
    )
