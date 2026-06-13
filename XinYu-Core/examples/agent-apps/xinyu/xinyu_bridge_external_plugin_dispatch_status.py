from __future__ import annotations

from typing import Any

from xinyu_external_plugins import (
    TRANSPORT_HTTP,
    TRANSPORT_MCP,
    TRANSPORT_NATIVE_BRIDGE,
    TRANSPORT_WEBSOCKET,
)


CODEX_EXECUTE_BRIDGE_METHOD = "codex_execute"
PRIVATE_NATIVE_PLUGIN_IDS = frozenset(
    {"xinyu_private_browser", "xinyu_computer_control", "xinyu_private_desktop"}
)
UNCONFIGURED_EXECUTOR_TRANSPORTS = frozenset({TRANSPORT_WEBSOCKET, TRANSPORT_MCP})


def dispatch_transport(request: dict[str, Any], deps: Any) -> str:
    return deps.safe_str(request.get("transport"))


def is_codex_delegate_dispatch(transport: str, request: dict[str, Any], deps: Any) -> bool:
    return (
        transport == TRANSPORT_NATIVE_BRIDGE
        and deps.safe_str(request.get("bridge_method")) == CODEX_EXECUTE_BRIDGE_METHOD
    )


def is_http_dispatch(transport: str) -> bool:
    return transport == TRANSPORT_HTTP


def is_private_native_dispatch(plugin_id: str, transport: str) -> bool:
    return transport == TRANSPORT_NATIVE_BRIDGE and plugin_id in PRIVATE_NATIVE_PLUGIN_IDS


def is_unconfigured_executor_transport(transport: str) -> bool:
    return transport in UNCONFIGURED_EXECUTOR_TRANSPORTS


__all__ = [
    "CODEX_EXECUTE_BRIDGE_METHOD",
    "PRIVATE_NATIVE_PLUGIN_IDS",
    "UNCONFIGURED_EXECUTOR_TRANSPORTS",
    "dispatch_transport",
    "is_codex_delegate_dispatch",
    "is_http_dispatch",
    "is_private_native_dispatch",
    "is_unconfigured_executor_transport",
]
