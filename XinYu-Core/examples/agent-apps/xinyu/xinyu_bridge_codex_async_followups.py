from __future__ import annotations

from typing import Any

from xinyu_async_exploration import (
    async_exploration_outbox_message as _async_exploration_outbox_message,
    update_async_exploration_from_codex,
)
from xinyu_bridge_values import safe_str
from xinyu_qq_outbox import enqueue_qq_outbox_message
from xinyu_tool_protocol import ActionOutcome, DELEGATED_LOCAL_RISK


def codex_delegate_action_outcome(result: Any, *, summary: str) -> dict[str, Any]:
    accepted_without_timeout = bool(result.accepted and not result.timed_out)
    return ActionOutcome(
        ok=accepted_without_timeout,
        tool="codex_delegate",
        summary=[summary],
        report_path=result.report_path,
        duration_ms=0,
        risk=DELEGATED_LOCAL_RISK,
        result="success" if accepted_without_timeout else "failure",
        load={
            "codex_exit_code": result.exit_code,
            "timeout": result.timed_out,
            "scheduled": True,
        },
        error_code="" if accepted_without_timeout else "codex_delegate_incomplete",
        notes=["codex_delegate_background_completion"],
    ).to_dict()


def codex_async_exploration_result_outbox_payload(
    update: dict[str, Any],
    *,
    resume_id: str,
    owner_intervention: str = "",
    has_error: bool = False,
    message_func: Any = _async_exploration_outbox_message,
) -> dict[str, Any]:
    compact_resume_id = safe_str(resume_id).strip()
    metadata: dict[str, Any] = {"resume_id": compact_resume_id}
    if has_error:
        metadata["has_error"] = True
    else:
        metadata["result_quality"] = update.get("result_quality", "unknown")
        metadata["owner_intervention"] = owner_intervention
    return {
        "message": message_func(update),
        "source": "async_exploration_result",
        "dedupe_key": f"async_exploration_result:{compact_resume_id}",
        "metadata": metadata,
    }


def notify_async_exploration_codex_result(
    runtime: Any,
    payload: dict[str, Any],
    *,
    async_resume_id: str,
    owner_intervention: str = "",
    result: Any | None = None,
    error: str = "",
    update_func: Any = update_async_exploration_from_codex,
    enqueue_func: Any = enqueue_qq_outbox_message,
    outbox_payload_func: Any = codex_async_exploration_result_outbox_payload,
) -> None:
    compact_resume_id = safe_str(async_resume_id).strip()
    if not compact_resume_id:
        return
    has_error = result is None
    if has_error:
        update = update_func(
            runtime.xinyu_dir,
            resume_id=compact_resume_id,
            result=None,
            error=error,
            owner_intervention=owner_intervention,
        )
    else:
        update = update_func(
            runtime.xinyu_dir,
            resume_id=compact_resume_id,
            result=result,
            owner_intervention=owner_intervention,
        )
    user_id = safe_str(payload.get("user_id")).strip() or runtime._owner_private_user_id()
    if not user_id:
        return
    outbox_payload = outbox_payload_func(
        update,
        resume_id=compact_resume_id,
        owner_intervention=owner_intervention,
        has_error=has_error,
    )
    enqueue_func(
        runtime.xinyu_dir,
        user_id=user_id,
        **outbox_payload,
    )
