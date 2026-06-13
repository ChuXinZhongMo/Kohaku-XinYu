from __future__ import annotations

from collections.abc import Callable
from typing import Any


async def handoff_codex_delegate_to_dream(
    runtime: Any,
    *,
    result: Any,
    text: str,
    use_global_turn_lock: bool,
    contain_errors: bool,
    handoff_func: Callable[..., Any],
    to_thread_func: Callable[..., Any],
    error_note_prefix: str,
) -> dict[str, Any]:
    if not (result.timed_out or not result.accepted):
        return {"notes": [], "error_note": ""}

    async def run_handoff() -> Any:
        return await to_thread_func(
            handoff_func,
            runtime.xinyu_dir,
            task_text=text,
            report_path=result.report_path,
            request_path=result.request_path,
            workspace_path=result.workspace_path,
            timed_out=result.timed_out,
            exit_code=result.exit_code,
        )

    try:
        if use_global_turn_lock:
            async with runtime._global_turn_lock:
                handoff = await run_handoff()
        else:
            handoff = await run_handoff()
        return {"notes": list(handoff.notes), "error_note": ""}
    except Exception as exc:
        if not contain_errors:
            raise
        return {"notes": [], "error_note": f"{error_note_prefix}:{type(exc).__name__}"}


async def settle_codex_delegate_action_experience(
    runtime: Any,
    payload: dict[str, Any],
    *,
    metadata: dict[str, Any],
    result: Any,
    action_outcome_func: Callable[..., dict[str, Any]],
) -> list[str]:
    action_request = metadata.get("action_layer_request")
    if not isinstance(action_request, dict):
        return []
    codex_outcome = action_outcome_func(
        result,
        summary=runtime._codex_completion_summary(result),
    )
    _, _, action_experience_notes = await runtime._settle_action_experience(
        payload,
        request=action_request,
        outcome=codex_outcome,
    )
    return list(action_experience_notes)
