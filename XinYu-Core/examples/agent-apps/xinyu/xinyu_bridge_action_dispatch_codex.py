from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_action_support import bridge_error_status_value


async def execute_codex_delegate_action(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    request: Any,
    request_dict: dict[str, Any],
    bridge_request_error_type: type[BaseException] | None,
    codex_response_to_outcome_func: Callable[..., dict[str, Any]],
    looks_like_owner_local_write_request_func: Callable[[str], bool],
    action_outcome_cls: Any,
    delegated_local_risk: str,
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    try:
        task_text = safe_str_func(request.params.get("task_text")).strip() or text
        codex_payload = runtime._build_model_codex_payload(payload, session_key=session_key, task_text=task_text)
        metadata = codex_payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            codex_payload["metadata"] = metadata
        metadata["delegated_by_action_layer"] = True
        if bool(metadata.get("is_owner_user")) and looks_like_owner_local_write_request_func(task_text):
            metadata["owner_local_write_approved"] = True
            metadata["owner_local_write_source"] = "owner_private_action_layer"
        metadata["action_layer_request"] = request_dict
        codex_response = await runtime.codex_execute(codex_payload)
        return codex_response_to_outcome_func(codex_response, request)
    except Exception as exc:
        if bridge_request_error_type is not None and isinstance(exc, bridge_request_error_type):
            status_value = bridge_error_status_value(exc)
            return action_outcome_cls.failed(
                tool="codex_delegate",
                summary=safe_str_func(getattr(exc, "message", str(exc))),
                error_code=f"bridge_request_error:{status_value}",
                risk=delegated_local_risk,
                notes=["codex_delegate_bridge_rejected"],
            ).to_dict()
        return action_outcome_cls.failed(
            tool="codex_delegate",
            summary="Codex \u59d4\u6d3e\u6ca1\u6709\u542f\u52a8\uff1a" + type(exc).__name__,
            error_code=type(exc).__name__,
            risk=delegated_local_risk,
            notes=["codex_delegate_bridge_exception"],
        ).to_dict()
