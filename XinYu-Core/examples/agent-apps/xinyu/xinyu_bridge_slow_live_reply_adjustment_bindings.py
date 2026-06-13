from __future__ import annotations

from typing import Any, Mapping


def apply_slow_live_visible_dedupe_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return deps["_runtime_apply_slow_live_visible_dedupe"](
        values["runtime"],
        values["session"],
        values["reply"],
        dedupe_func=deps["dedupe_visible_reply"],
    )


def apply_slow_live_stale_context_repair_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    semantic_fast = deps["xinyu_bridge_semantic_fast_routes"]
    return deps["_runtime_apply_slow_live_stale_context_repair"](
        values["runtime"],
        values["session"],
        values["payload"],
        reply=values["reply"],
        user_text=values["user_text"],
        final_guard_flags=values["final_guard_flags"],
        blocked_by_delegate=values["blocked_by_delegate"],
        owner_private_match_func=deps["_owner_private_payload_matches"],
        stale_reply_func=semantic_fast.reply_looks_like_stale_plan_residue,
        repair_reply_func=semantic_fast.owner_private_direct_repair_reply,
        normalize_func=deps["normalize_bridge_reply"],
        dedupe_func=deps["_dedupe"],
    )


def apply_slow_live_life_reply_policy_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return deps["_runtime_apply_slow_live_life_reply_policy"](
        values["runtime"],
        values["session"],
        reply=values["reply"],
        user_text=values["user_text"],
        life_reply_policy=values["life_reply_policy"],
        blocked_by_delegate=values["blocked_by_delegate"],
        policy_func=deps["apply_life_reply_policy"],
        safe_str_func=deps["_safe_str"],
    )


def apply_slow_live_current_reference_repair_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return deps["_runtime_apply_slow_live_current_reference_repair"](
        values["runtime"],
        values["session"],
        values["payload"],
        reply=values["reply"],
        user_text=values["user_text"],
        final_guard_flags=values["final_guard_flags"],
        blocked_by_delegate=values["blocked_by_delegate"],
        owner_private_match_func=deps["_owner_private_payload_matches"],
        repair_func=deps["repair_current_reference_reply"],
        safe_str_func=deps["_safe_str"],
        dedupe_func=deps["_dedupe"],
    )


def apply_slow_live_reply_bubble_policy_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return deps["_runtime_apply_slow_live_reply_bubble_policy"](
        values["runtime"],
        values["session"],
        reply=values["reply"],
        user_text=values["user_text"],
        dialogue_tail=values["dialogue_tail"],
        final_guard_flags=values["final_guard_flags"],
        false_single_bubble_reply=deps["FALSE_SINGLE_BUBBLE_REPLY"],
        dedupe_func=deps["_dedupe"],
    )


def apply_slow_live_sticker_reply_override_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return deps["_runtime_apply_slow_live_sticker_reply_override"](
        values["runtime"],
        values["session"],
        values["payload"],
        reply=values["reply"],
        user_text=values["user_text"],
    )


def apply_slow_live_style_pressure_empty_fallback_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return deps["_runtime_apply_slow_live_style_pressure_empty_fallback"](
        values["runtime"],
        values["session"],
        reply=values["reply"],
        final_guard_flags=values["final_guard_flags"],
        style_pressure_empty_reply=deps["STYLE_PRESSURE_EMPTY_REPLY"],
        dedupe_func=deps["_dedupe"],
    )


async def recover_slow_live_empty_visible_reply_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_recover_slow_live_empty_visible_reply"](
        values["runtime"],
        values["session"],
        values["payload"],
        reply=values["reply"],
        user_text=values["user_text"],
        final_guard_flags=values["final_guard_flags"],
        rendered=values["rendered"],
        renderer_reason=values["renderer_reason"],
        recalled_context=values["recalled_context"],
        blocked_by_delegate=values["blocked_by_delegate"],
        owner_private_match_func=deps["_owner_private_payload_matches"],
        safe_str_func=deps["_safe_str"],
        dedupe_func=deps["_dedupe"],
    )


async def apply_slow_live_final_reply_guard_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_apply_slow_live_final_reply_guard"](
        values["runtime"],
        values["session"],
        values["payload"],
        reply=values["reply"],
        user_text=values["user_text"],
        recalled_context=values["recalled_context"],
        trace_route_stage=values["trace_route_stage"],
        codex_delegate_blocked=values["codex_delegate_blocked"],
        render_func=deps["render_outward_reply_with_trace"],
        expression_record_func=deps["record_expression_self_learning_event"],
        safe_str_func=deps["_safe_str"],
        dedupe_func=deps["_dedupe"],
    )


async def apply_slow_live_outward_renderer_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_apply_slow_live_outward_renderer"](
        values["runtime"],
        values["session"],
        values["payload"],
        reply=values["reply"],
        draft_reply=values["draft_reply"],
        user_text=values["user_text"],
        recalled_context=values["recalled_context"],
        trace_route_stage=values["trace_route_stage"],
        blocked_by_delegate=values["blocked_by_delegate"],
        render_func=deps["render_outward_reply_with_trace"],
        safe_str_func=deps["_safe_str"],
    )


async def apply_slow_live_reply_adjustment_pipeline_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return await deps["_runtime_apply_slow_live_reply_adjustment_pipeline"](
        values["runtime"],
        values["session"],
        values["payload"],
        reply=values["reply"],
        draft_reply=values["draft_reply"],
        user_text=values["user_text"],
        recalled_context=values["recalled_context"],
        life_reply_policy=values["life_reply_policy"],
        trace_route_stage=values["trace_route_stage"],
        blocked_by_delegate=values["blocked_by_delegate"],
        codex_delegate_blocked=values["codex_delegate_blocked"],
        outward_renderer_func=deps["apply_slow_live_outward_renderer"],
        final_reply_guard_func=deps["apply_slow_live_final_reply_guard"],
        visible_dedupe_func=deps["apply_slow_live_visible_dedupe"],
        stale_context_repair_func=deps["apply_slow_live_stale_context_repair"],
        life_reply_policy_func=deps["apply_slow_live_life_reply_policy"],
        current_reference_repair_func=deps["apply_slow_live_current_reference_repair"],
        reply_bubble_policy_func=deps["apply_slow_live_reply_bubble_policy"],
        sticker_reply_override_func=deps["apply_slow_live_sticker_reply_override"],
        style_pressure_empty_fallback_func=deps["apply_slow_live_style_pressure_empty_fallback"],
        empty_visible_recovery_func=deps["recover_slow_live_empty_visible_reply"],
    )
