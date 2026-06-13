from __future__ import annotations

from typing import Any

from xinyu_bridge_external_plugin_payload import ExternalPluginCallPayload


def prepared_request(prepared: dict[str, Any]) -> dict[str, Any]:
    request = prepared.get("request")
    return request if isinstance(request, dict) else {}


def call_execute_enabled(call: ExternalPluginCallPayload, deps: Any) -> bool:
    return deps.as_bool(call.raw.get("execute"), default=True)


def http_timeout_seconds(call: ExternalPluginCallPayload, deps: Any) -> int:
    return deps.as_int(call.raw.get("timeout_seconds"), 30)


def codex_delegate_payload(call: ExternalPluginCallPayload, request: dict[str, Any]) -> dict[str, Any]:
    payload = request.get("payload")
    codex_payload = dict(payload) if isinstance(payload, dict) else {}
    metadata = codex_payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata.setdefault("is_owner_user", call.context.owner_private)
    metadata["external_plugin_call"] = True
    metadata["external_plugin_id"] = call.plugin_id
    metadata["external_plugin_capability"] = call.capability
    codex_payload["metadata"] = metadata
    return codex_payload


__all__ = [
    "call_execute_enabled",
    "codex_delegate_payload",
    "http_timeout_seconds",
    "prepared_request",
]
