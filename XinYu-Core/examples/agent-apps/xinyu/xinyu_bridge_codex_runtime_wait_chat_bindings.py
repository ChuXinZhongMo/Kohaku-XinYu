from __future__ import annotations

from typing import Any, Mapping


async def transition_wait_to_think_reply_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    runtime = values["runtime"]
    return await deps["_runtime_transition_wait_to_think_reply"](
        runtime,
        values["payload"],
        user_text=values["user_text"],
        draft_reply=values["draft_reply"],
        wait_task=values["wait_task"],
        session_key=values["session_key"],
        timeout_seconds=deps["CODEX_DEFAULT_TIMEOUT_SECONDS"],
        window_title=deps["CODEX_VISIBLE_WINDOW_TITLE"],
        execution_plan_func=getattr(runtime, "_wait_to_think_execution_plan", deps["wait_to_think_execution_plan"]),
        create_closure_func=deps["create_async_exploration_closure"],
        build_payload_func=deps["build_wait_to_think_codex_payload"],
        update_func=deps["update_async_exploration_from_codex"],
        enqueue_func=deps["enqueue_qq_outbox_message"],
        message_func=deps["_async_exploration_outbox_message"],
    )


async def apply_chat_codex_reply_delegates_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> Any:
    return await deps["_runtime_apply_chat_codex_reply_delegates"](
        values["runtime"],
        values["session"],
        values["payload"],
        user_text=values["user_text"],
        draft_reply=values["draft_reply"],
        session_key=values["session_key"],
        self_code_task=values["self_code_task"],
        model_codex_task=values["model_codex_task"],
        wait_to_think_task=values["wait_to_think_task"],
        scheduled_reply_func=deps["compose_codex_chat_scheduled_reply"],
        watchdog_message_func=deps["compose_watchdog_visible_message"],
        mark_self_code_scheduled_func=deps["mark_self_code_execution_scheduled"],
    )
