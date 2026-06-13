from __future__ import annotations

from typing import Any

from xinyu_bridge_runtime_autonomous_aliases import install_autonomous_maintenance_aliases
from xinyu_bridge_runtime_health_aliases import install_health_aliases
from xinyu_bridge_runtime_lifecycle_aliases import install_lifecycle_aliases
from xinyu_bridge_runtime_metabolism_aliases import install_metabolism_aliases
from xinyu_bridge_runtime_proactive_context_aliases import install_proactive_context_aliases


def install_runtime_life_aliases(runtime_cls: type[Any]) -> type[Any]:
    install_health_aliases(runtime_cls)
    install_lifecycle_aliases(runtime_cls)
    install_metabolism_aliases(runtime_cls)
    install_autonomous_maintenance_aliases(runtime_cls)
    install_proactive_context_aliases(runtime_cls)
    return runtime_cls
