from __future__ import annotations

from typing import Any

import xinyu_bridge_health_snapshot


def install_health_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls.health_snapshot = xinyu_bridge_health_snapshot.runtime_health_snapshot
    runtime_cls.health = xinyu_bridge_health_snapshot.runtime_health
    runtime_cls._metabolism_health = xinyu_bridge_health_snapshot.metabolism_health
    runtime_cls._autonomous_maintenance_health = xinyu_bridge_health_snapshot.autonomous_maintenance_health
