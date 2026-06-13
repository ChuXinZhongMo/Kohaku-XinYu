from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from xinyu_bridge_errors import BridgeRequestError


@dataclass(frozen=True)
class ExternalPluginCallPayload:
    raw: dict[str, Any]
    plugin_id: str
    capability: str
    args: dict[str, Any]
    context: Any


def normalize_external_plugin_payload(payload: dict[str, Any], deps: Any) -> ExternalPluginCallPayload:
    safe_str = deps.safe_str
    plugin_id = safe_str(payload.get("plugin_id") or payload.get("pluginId")).strip()
    capability = safe_str(payload.get("capability") or payload.get("capability_name")).strip()
    if not plugin_id or not capability:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "plugin_id and capability are required")

    args = payload.get("args")
    return ExternalPluginCallPayload(
        raw=payload,
        plugin_id=plugin_id,
        capability=capability,
        args=args if isinstance(args, dict) else {},
        context=deps.build_context(payload),
    )


def plugin_config(plugin_state: dict[str, Any]) -> dict[str, Any]:
    config = plugin_state.get("config")
    return config if isinstance(config, dict) else {}


def apply_plugin_config_defaults(
    call: ExternalPluginCallPayload,
    plugin_state: dict[str, Any],
    deps: Any,
) -> dict[str, Any]:
    if call.plugin_id != "kohaku_terrarium":
        return call.args

    safe_str = deps.safe_str
    configured_base_url = safe_str(plugin_config(plugin_state).get("base_url")).strip()
    if safe_str(call.args.get("base_url")).strip() or not configured_base_url:
        return call.args

    args = dict(call.args)
    args["base_url"] = configured_base_url
    return args


__all__ = [
    "ExternalPluginCallPayload",
    "apply_plugin_config_defaults",
    "normalize_external_plugin_payload",
    "plugin_config",
]
