from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_async_exploration import (
    async_exploration_outbox_message as _async_exploration_outbox_message,
    create_async_exploration_closure,
    update_async_exploration_from_codex,
)
from xinyu_bridge_codex_wait import build_wait_to_think_codex_payload, wait_to_think_execution_plan
from xinyu_bridge_values import safe_str
from xinyu_qq_outbox import enqueue_qq_outbox_message


DEFAULT_WAIT_TO_THINK_TRANSITION = "我去后台验证一下，等结果出来再接着说。"


async def transition_wait_to_think_reply(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    draft_reply: str,
    wait_task: str,
    session_key: str,
    timeout_seconds: int = 3600,
    window_title: str = "Xinyu codex",
    execution_plan_func: Callable[..., str] | None = None,
    create_closure_func: Callable[..., dict[str, Any]] = create_async_exploration_closure,
    build_payload_func: Callable[..., dict[str, Any]] = build_wait_to_think_codex_payload,
    update_func: Callable[..., dict[str, Any]] = update_async_exploration_from_codex,
    enqueue_func: Callable[..., Any] = enqueue_qq_outbox_message,
    message_func: Callable[[dict[str, Any]], str] = _async_exploration_outbox_message,
    default_transition: str = DEFAULT_WAIT_TO_THINK_TRANSITION,
) -> tuple[str, dict[str, Any]]:
    execution_plan = execution_plan_func or getattr(runtime, "_wait_to_think_execution_plan", wait_to_think_execution_plan)
    closure = create_closure_func(
        runtime.xinyu_dir,
        payload,
        session_key=session_key,
        user_text=user_text,
        draft_reply=draft_reply,
        task_text=wait_task,
        delegation_reason="model_wait_to_think",
        execution_plan=execution_plan(wait_task, user_text=user_text),
    )
    transition = safe_str(closure.get("transition_message")).strip() or default_transition
    resume_id = safe_str(closure.get("resume_id")).strip()
    codex_payload = build_payload_func(
        payload,
        session_key=session_key,
        wait_task=wait_task,
        resume_id=resume_id,
        user_text=user_text,
        timeout_seconds=timeout_seconds,
        window_title=window_title,
    )
    try:
        await runtime.codex_execute(codex_payload)
        note = "wait_to_think_codex_scheduled"
    except Exception as exc:
        update = update_func(
            runtime.xinyu_dir,
            resume_id=resume_id or "wait-unknown",
            result=None,
            error=f"{type(exc).__name__}: {exc}",
        )
        note = "wait_to_think_schedule_error"
        user_id = safe_str(payload.get("user_id")).strip() or runtime._owner_private_user_id()
        if user_id:
            enqueue_func(
                runtime.xinyu_dir,
                user_id=user_id,
                message=message_func(update),
                source="async_exploration_failure",
                dedupe_key=f"async_exploration_failure:{resume_id or user_text[:80]}",
                metadata={"resume_id": resume_id, "has_error": True},
            )
    return transition, {
        "notes": [
            safe_str(note),
            *[safe_str(item) for item in closure.get("notes", [])],
        ],
        "resume_id": resume_id,
    }
