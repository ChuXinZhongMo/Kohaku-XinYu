from __future__ import annotations

from typing import Any

import xinyu_bridge_private_desktop_routes


def install_private_desktop_route_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls.desktop_private_desktop_snapshot = (
        xinyu_bridge_private_desktop_routes.desktop_private_desktop_snapshot
    )
    runtime_cls.desktop_private_desktop_live_state = (
        xinyu_bridge_private_desktop_routes.desktop_private_desktop_live_state
    )
    runtime_cls.desktop_private_desktop_frame = xinyu_bridge_private_desktop_routes.desktop_private_desktop_frame
    runtime_cls.desktop_private_desktop_observe = xinyu_bridge_private_desktop_routes.desktop_private_desktop_observe
    runtime_cls.desktop_private_desktop_start = xinyu_bridge_private_desktop_routes.desktop_private_desktop_start
    runtime_cls.desktop_private_desktop_stop = xinyu_bridge_private_desktop_routes.desktop_private_desktop_stop
