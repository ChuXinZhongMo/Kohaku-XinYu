from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_action_dispatch_codex import execute_codex_delegate_action
from xinyu_bridge_action_dispatch_external import execute_external_plugin_action


async def execute_action_request(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    request: Any,
    request_dict: dict[str, Any],
    bridge_request_error_type: type[BaseException] | None,
    codex_response_to_outcome_func: Callable[..., dict[str, Any]],
    external_response_to_outcome_func: Callable[..., dict[str, Any]],
    looks_like_owner_local_write_request_func: Callable[[str], bool],
    action_outcome_cls: Any,
    delegated_local_risk: str,
    safe_str_func: Callable[..., str],
    to_thread_func: Callable[..., Any],
) -> dict[str, Any]:
    if request.tool == "codex_delegate":
        return await execute_codex_delegate_action(
            runtime,
            payload,
            text=text,
            session_key=session_key,
            request=request,
            request_dict=request_dict,
            bridge_request_error_type=bridge_request_error_type,
            codex_response_to_outcome_func=codex_response_to_outcome_func,
            looks_like_owner_local_write_request_func=looks_like_owner_local_write_request_func,
            action_outcome_cls=action_outcome_cls,
            delegated_local_risk=delegated_local_risk,
            safe_str_func=safe_str_func,
        )
    if request.tool == "external_plugin_call":
        return await execute_external_plugin_action(
            runtime,
            request=request,
            bridge_request_error_type=bridge_request_error_type,
            external_response_to_outcome_func=external_response_to_outcome_func,
            action_outcome_cls=action_outcome_cls,
            safe_str_func=safe_str_func,
        )
    return await to_thread_func(
        runtime.action_layer.execute,
        request,
        payload,
        bridge_snapshot=runtime.health_snapshot(),
    )
