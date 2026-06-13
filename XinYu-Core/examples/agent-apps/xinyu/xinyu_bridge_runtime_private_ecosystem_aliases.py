from __future__ import annotations

from typing import Any

import xinyu_bridge_private_ecosystem_routes


def install_private_ecosystem_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls.desktop_private_ecosystem_snapshot = (
        xinyu_bridge_private_ecosystem_routes.desktop_private_ecosystem_snapshot
    )
    runtime_cls.desktop_private_ecosystem_pause = xinyu_bridge_private_ecosystem_routes.desktop_private_ecosystem_pause
    runtime_cls.desktop_private_ecosystem_grant = xinyu_bridge_private_ecosystem_routes.desktop_private_ecosystem_grant
    runtime_cls.desktop_private_ecosystem_tick = xinyu_bridge_private_ecosystem_routes.desktop_private_ecosystem_tick
    runtime_cls.desktop_private_browser_snapshot = xinyu_bridge_private_ecosystem_routes.desktop_private_browser_snapshot
    runtime_cls.desktop_private_browser_action = xinyu_bridge_private_ecosystem_routes.desktop_private_browser_action
    runtime_cls._append_private_ecosystem_note = xinyu_bridge_private_ecosystem_routes.append_private_ecosystem_note
