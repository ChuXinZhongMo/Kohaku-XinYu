from __future__ import annotations

from typing import Any

import xinyu_bridge_external_plugin_routes


def install_external_plugin_route_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls.external_plugin_manifest = xinyu_bridge_external_plugin_routes.external_plugin_manifest
    runtime_cls.external_plugin_config = xinyu_bridge_external_plugin_routes.external_plugin_config
    runtime_cls.external_plugin_install = xinyu_bridge_external_plugin_routes.external_plugin_install
    runtime_cls.external_plugin_call = xinyu_bridge_external_plugin_routes.external_plugin_call
    runtime_cls._maybe_run_self_thought_external_plugin = (
        xinyu_bridge_external_plugin_routes.maybe_run_self_thought_external_plugin
    )
