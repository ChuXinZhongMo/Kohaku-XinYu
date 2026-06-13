from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_action_support import bridge_error_status_value


async def execute_external_plugin_action(
    runtime: Any,
    *,
    request: Any,
    bridge_request_error_type: type[BaseException] | None,
    external_response_to_outcome_func: Callable[..., dict[str, Any]],
    action_outcome_cls: Any,
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    try:
        external_payload = dict(request.params)
        external_payload.setdefault("source", request.source)
        external_payload.setdefault("execute", True)
        context = external_payload.get("context")
        if not isinstance(context, dict):
            context = {}
        context.setdefault("source", request.source)
        context.setdefault("owner_private", True)
        context.setdefault("reason", "owner explicit external plugin request")
        external_payload["context"] = context
        external_response = await runtime.external_plugin_call(external_payload)
        return external_response_to_outcome_func(external_response, request)
    except Exception as exc:
        if bridge_request_error_type is not None and isinstance(exc, bridge_request_error_type):
            status_value = bridge_error_status_value(exc)
            return action_outcome_cls.failed(
                tool="external_plugin_call",
                summary=safe_str_func(getattr(exc, "message", str(exc))),
                error_code=f"bridge_request_error:{status_value}",
                risk=request.risk,
                notes=["external_plugin_bridge_rejected"],
            ).to_dict()
        return action_outcome_cls.failed(
            tool="external_plugin_call",
            summary=f"external plugin call did not start: {type(exc).__name__}",
            error_code=type(exc).__name__,
            risk=request.risk,
            notes=["external_plugin_bridge_exception"],
        ).to_dict()
