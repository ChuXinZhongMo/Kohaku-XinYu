from __future__ import annotations

from typing import Any

from xinyu_bridge_runtime_external_plugin_aliases import install_external_plugin_route_aliases
from xinyu_bridge_runtime_intervention_aliases import install_intervention_route_aliases
from xinyu_bridge_runtime_proactive_route_aliases import install_proactive_route_aliases
from xinyu_bridge_runtime_utility_route_aliases import install_utility_route_aliases


def install_runtime_route_aliases(runtime_cls: type[Any]) -> type[Any]:
    install_intervention_route_aliases(runtime_cls)
    install_external_plugin_route_aliases(runtime_cls)
    install_proactive_route_aliases(runtime_cls)
    install_utility_route_aliases(runtime_cls)
    return runtime_cls
