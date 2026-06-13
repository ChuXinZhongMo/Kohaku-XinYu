from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_state_mapping import DataclassMappingState
from xinyu_bridge_values import safe_str
from xinyu_self_code_approval import mark_self_code_execution_scheduled
from xinyu_visible_persona_voice import compose_codex_chat_scheduled_reply, compose_watchdog_visible_message


@dataclass(eq=False)
class ChatCodexReplyDelegateState(DataclassMappingState):
    reply: str
    direct_codex_task: str
    wait_to_think_sidecar: dict[str, Any]
    model_codex_delegate_note: str


async def apply_chat_codex_reply_delegates(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    draft_reply: str,
    session_key: str,
    self_code_task: str,
    model_codex_task: str,
    wait_to_think_task: str,
    scheduled_reply_func: Callable[[str], str] = compose_codex_chat_scheduled_reply,
    watchdog_message_func: Callable[..., str] = compose_watchdog_visible_message,
    mark_self_code_scheduled_func: Callable[..., Any] = mark_self_code_execution_scheduled,
) -> ChatCodexReplyDelegateState:
    reply = draft_reply
    direct_codex_task = ""
    wait_to_think_sidecar: dict[str, Any] = {"notes": []}
    model_codex_delegate_note = ""

    if wait_to_think_task and not self_code_task and not model_codex_task:
        reply, wait_to_think_sidecar = await runtime._transition_wait_to_think_reply(
            payload,
            user_text=user_text,
            draft_reply=draft_reply,
            wait_task=wait_to_think_task,
            session_key=session_key,
        )
        model_codex_delegate_note = "wait_to_think:scheduled"
        runtime._replace_last_assistant_message(session.agent, reply)
    elif self_code_task:
        codex_state = runtime._codex_delegate_running()
        if codex_state.get("running"):
            reply = runtime._codex_busy_reply(codex_state)
            model_codex_delegate_note = "owner_self_code_iteration:codex_busy"
        else:
            self_code_delegate = runtime._build_self_code_iteration_codex_payload(
                payload,
                session_key=session_key,
                task_text=self_code_task,
            )
            codex_payload = self_code_delegate["payload"]
            approval_id = self_code_delegate["approval_id"]
            try:
                watchdog_snapshot = runtime._prepare_self_code_watchdog_payload(
                    codex_payload,
                    approval_id=approval_id,
                )
                codex_response = await runtime.codex_execute(codex_payload)
                mark_self_code_scheduled_func(
                    runtime.xinyu_dir,
                    approval_id=approval_id,
                    job_id=safe_str(codex_response.get("request_path") or codex_response.get("report_path") or ""),
                    watchdog_snapshot_id=safe_str(watchdog_snapshot.get("snapshot_id"), "none"),
                    watchdog_manifest_path=safe_str(watchdog_snapshot.get("manifest_path"), "none"),
                )
                reply = scheduled_reply_func("self_code")
                model_codex_delegate_note = "owner_self_code_iteration:scheduled"
            except BridgeRequestError as exc:
                reply = exc.message
                model_codex_delegate_note = f"owner_self_code_iteration_error:{exc.status.value}"
            except Exception as exc:
                reply = watchdog_message_func(
                    "self_code_watchdog_failed",
                    error=f"{type(exc).__name__}: {exc}",
                )
                model_codex_delegate_note = f"owner_self_code_iteration_watchdog_error:{type(exc).__name__}"
        runtime._replace_last_assistant_message(session.agent, reply)
    elif model_codex_task:
        if runtime._can_model_delegate_codex(payload, task_text=model_codex_task):
            codex_payload = runtime._build_model_codex_payload(
                payload,
                session_key=session_key,
                task_text=model_codex_task,
            )
            try:
                await runtime.codex_execute(codex_payload)
                reply = scheduled_reply_func("model_delegate")
                model_codex_delegate_note = "model_codex_delegate:scheduled"
            except BridgeRequestError as exc:
                reply = exc.message
                model_codex_delegate_note = f"model_codex_delegate_error:{exc.status.value}"
            runtime._replace_last_assistant_message(session.agent, reply)
        else:
            reply = scheduled_reply_func("not_owner_private")
            model_codex_delegate_note = "model_codex_delegate_rejected:not_owner_private"
            runtime._replace_last_assistant_message(session.agent, reply)

    if not self_code_task and not model_codex_task and not wait_to_think_task:
        direct_codex_task = runtime._owner_direct_codex_task(
            payload,
            user_text=user_text,
            reply=draft_reply,
            session_key=session_key,
        )
        if direct_codex_task:
            codex_payload = runtime._build_model_codex_payload(
                payload,
                session_key=session_key,
                task_text=direct_codex_task,
            )
            codex_payload["metadata"]["delegated_by_owner_directive"] = True
            try:
                await runtime.codex_execute(codex_payload)
                reply = scheduled_reply_func("owner_direct")
                model_codex_delegate_note = "owner_direct_codex_delegate:scheduled"
            except BridgeRequestError as exc:
                reply = exc.message
                model_codex_delegate_note = f"owner_direct_codex_delegate_error:{exc.status.value}"
            runtime._replace_last_assistant_message(session.agent, reply)

    return ChatCodexReplyDelegateState(
        reply=reply,
        direct_codex_task=direct_codex_task,
        wait_to_think_sidecar=wait_to_think_sidecar,
        model_codex_delegate_note=model_codex_delegate_note,
    )
