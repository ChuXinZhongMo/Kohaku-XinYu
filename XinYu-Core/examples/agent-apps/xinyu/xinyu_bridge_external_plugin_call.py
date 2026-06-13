from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Callable

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_external_plugin_dispatch import dispatch_external_plugin_call
from xinyu_bridge_external_plugin_payload import (
    apply_plugin_config_defaults,
    normalize_external_plugin_payload,
)
from xinyu_bridge_external_plugin_response import (
    prepared_boundary_blocked_response,
    runtime_boundary_blocked_response,
)
from xinyu_external_plugins import (
    TRANSPORT_HTTP,
    TRANSPORT_MCP,
    TRANSPORT_NATIVE_BRIDGE,
    TRANSPORT_WEBSOCKET,
)


@dataclass(frozen=True)
class ExternalPluginCallDeps:
    ensure_open: Callable[[Any], None]
    ensure_payload: Callable[[dict[str, Any] | None], dict[str, Any]]
    sessions: Callable[[Any], int]
    build_context: Callable[[dict[str, Any]], Any]
    summarize: Callable[..., list[str]]
    as_bool: Callable[..., bool]
    as_int: Callable[..., int]
    safe_str: Callable[..., str]
    runtime_allowed: Callable[..., tuple[bool, str, dict[str, Any]]]
    prepare_call: Callable[..., Any]
    execute_http: Callable[..., dict[str, Any]]
    execute_private_native: Callable[..., dict[str, Any]]


async def external_plugin_call_impl(
    runtime: Any,
    payload: dict[str, Any] | None,
    deps: ExternalPluginCallDeps,
) -> dict[str, Any]:
    deps.ensure_open(runtime)
    payload = deps.ensure_payload(payload)
    call = normalize_external_plugin_payload(payload, deps)
    allowed, reason, plugin_state = deps.runtime_allowed(
        runtime.xinyu_dir,
        call.plugin_id,
        proactive=call.context.proactive,
    )
    if not allowed:
        return runtime_boundary_blocked_response(
            plugin_id=call.plugin_id,
            capability=call.capability,
            reason=reason,
            plugin_state=plugin_state,
            sessions=deps.sessions(runtime),
        )

    args = apply_plugin_config_defaults(call, plugin_state, deps)
    prepared = deps.prepare_call(call.plugin_id, call.capability, args, call.context).to_dict()
    decision = prepared.get("decision") if isinstance(prepared.get("decision"), dict) else {}
    if not bool(decision.get("ok")):
        return prepared_boundary_blocked_response(
            plugin_id=call.plugin_id,
            capability=call.capability,
            prepared=prepared,
            decision=decision,
            sessions=deps.sessions(runtime),
            safe_str=deps.safe_str,
        )

    return await dispatch_external_plugin_call(
        runtime,
        call,
        prepared=prepared,
        args=args,
        deps=deps,
    )
