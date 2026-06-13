from __future__ import annotations

from typing import Any

from xinyu_bridge_runtime_desktop_event_aliases import install_desktop_event_aliases
from xinyu_bridge_runtime_desktop_projection_aliases import install_desktop_projection_aliases
from xinyu_bridge_runtime_desktop_recent_aliases import install_desktop_recent_aliases
from xinyu_bridge_runtime_desktop_self_action_aliases import install_desktop_self_action_aliases
from xinyu_bridge_runtime_desktop_snapshot_aliases import install_desktop_snapshot_aliases
from xinyu_bridge_runtime_private_desktop_aliases import install_private_desktop_route_aliases
from xinyu_bridge_runtime_private_ecosystem_aliases import install_private_ecosystem_aliases


def install_private_desktop_aliases(runtime_cls: type[Any]) -> None:
    install_private_ecosystem_aliases(runtime_cls)
    install_private_desktop_route_aliases(runtime_cls)


def install_runtime_desktop_aliases(runtime_cls: type[Any]) -> type[Any]:
    install_private_desktop_aliases(runtime_cls)
    install_desktop_snapshot_aliases(runtime_cls)
    install_desktop_event_aliases(runtime_cls)
    install_desktop_recent_aliases(runtime_cls)
    install_desktop_projection_aliases(runtime_cls)
    install_desktop_self_action_aliases(runtime_cls)
    return runtime_cls
