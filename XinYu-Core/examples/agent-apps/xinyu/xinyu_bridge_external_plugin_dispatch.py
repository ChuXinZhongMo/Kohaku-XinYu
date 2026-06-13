from __future__ import annotations

import asyncio
from http import HTTPStatus
from typing import Any

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_external_plugin_dispatch_payload import (
    call_execute_enabled,
    codex_delegate_payload,
    http_timeout_seconds,
    prepared_request,
)
from xinyu_bridge_external_plugin_dispatch_status import (
    PRIVATE_NATIVE_PLUGIN_IDS,
    dispatch_transport,
    is_codex_delegate_dispatch,
    is_http_dispatch,
    is_private_native_dispatch,
    is_unconfigured_executor_transport,
)
from xinyu_bridge_external_plugin_dispatch_trace import (
    codex_delegate_execution_trace,
    empty_execution_trace,
)
from xinyu_bridge_external_plugin_payload import ExternalPluginCallPayload
from xinyu_bridge_external_plugin_response import (
    codex_execution_response,
    http_execution_response,
    prepared_response,
    private_native_execution_response,
    transport_not_configured_response,
)


async def _execute_codex_delegate(
    runtime: Any,
    call: ExternalPluginCallPayload,
    prepared: dict[str, Any],
    request: dict[str, Any],
    deps: Any,
) -> dict[str, Any]:
    result = await runtime.codex_execute(codex_delegate_payload(call, request))
    execution = codex_delegate_execution_trace(result)
    return codex_execution_response(
        plugin_id=call.plugin_id,
        capability=call.capability,
        prepared=prepared,
        execution=execution,
        result=result,
        sessions=deps.sessions(runtime),
        safe_str=deps.safe_str,
    )


async def _execute_http(
    runtime: Any,
    call: ExternalPluginCallPayload,
    prepared: dict[str, Any],
    deps: Any,
) -> dict[str, Any]:
    execution = await asyncio.to_thread(
        deps.execute_http,
        prepared,
        timeout_seconds=http_timeout_seconds(call, deps),
    )
    return http_execution_response(
        plugin_id=call.plugin_id,
        capability=call.capability,
        prepared=prepared,
        execution=execution,
        summary=deps.summarize(
            plugin_id=call.plugin_id,
            capability=call.capability,
            prepared=prepared,
            execution=execution,
        ),
        sessions=deps.sessions(runtime),
        safe_str=deps.safe_str,
    )


async def _execute_private_native(
    runtime: Any,
    call: ExternalPluginCallPayload,
    prepared: dict[str, Any],
    args: dict[str, Any],
    deps: Any,
) -> dict[str, Any]:
    execution = await asyncio.to_thread(
        deps.execute_private_native,
        runtime.xinyu_dir,
        call.plugin_id,
        call.capability,
        args,
        call.context,
    )
    return private_native_execution_response(
        plugin_id=call.plugin_id,
        capability=call.capability,
        prepared=prepared,
        execution=execution,
        sessions=deps.sessions(runtime),
        safe_str=deps.safe_str,
    )


async def dispatch_external_plugin_call(
    runtime: Any,
    call: ExternalPluginCallPayload,
    *,
    prepared: dict[str, Any],
    args: dict[str, Any],
    deps: Any,
) -> dict[str, Any]:
    request = prepared_request(prepared)
    if not call_execute_enabled(call, deps):
        return prepared_response(
            plugin_id=call.plugin_id,
            capability=call.capability,
            prepared=prepared,
            summary=deps.summarize(
                plugin_id=call.plugin_id,
                capability=call.capability,
                prepared=prepared,
                execution=empty_execution_trace(),
            ),
            sessions=deps.sessions(runtime),
        )

    transport = dispatch_transport(request, deps)
    if is_codex_delegate_dispatch(transport, request, deps):
        return await _execute_codex_delegate(runtime, call, prepared, request, deps)

    if is_http_dispatch(transport):
        return await _execute_http(runtime, call, prepared, deps)

    if is_private_native_dispatch(call.plugin_id, transport):
        return await _execute_private_native(runtime, call, prepared, args, deps)

    if is_unconfigured_executor_transport(transport):
        return transport_not_configured_response(
            plugin_id=call.plugin_id,
            capability=call.capability,
            prepared=prepared,
            transport=transport,
            sessions=deps.sessions(runtime),
        )

    raise BridgeRequestError(HTTPStatus.BAD_REQUEST, f"unsupported external plugin transport: {transport}")


__all__ = ["PRIVATE_NATIVE_PLUGIN_IDS", "dispatch_external_plugin_call"]
