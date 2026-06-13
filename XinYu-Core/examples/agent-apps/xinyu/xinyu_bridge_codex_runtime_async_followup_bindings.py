from __future__ import annotations

from typing import Any, Mapping


def codex_delegate_action_outcome_runtime(
    result: Any,
    *,
    summary: str,
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return deps["_runtime_codex_delegate_action_outcome"](result, summary=summary)


def codex_async_exploration_result_outbox_payload_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> dict[str, Any]:
    return deps["_runtime_codex_async_exploration_result_outbox_payload"](
        values["update"],
        resume_id=values["resume_id"],
        owner_intervention=values["owner_intervention"],
        has_error=values["has_error"],
        message_func=deps["_async_exploration_outbox_message"],
    )


def notify_async_exploration_codex_result_runtime(
    values: Mapping[str, Any],
    deps: Mapping[str, Any],
) -> None:
    deps["_runtime_notify_async_exploration_codex_result"](
        values["runtime"],
        values["payload"],
        async_resume_id=values["async_resume_id"],
        owner_intervention=values["owner_intervention"],
        result=values["result"],
        error=values["error"],
        update_func=deps["update_async_exploration_from_codex"],
        enqueue_func=deps["enqueue_qq_outbox_message"],
        outbox_payload_func=deps["codex_async_exploration_result_outbox_payload"],
    )
