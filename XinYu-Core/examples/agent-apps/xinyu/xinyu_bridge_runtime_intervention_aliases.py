from __future__ import annotations

from typing import Any

import xinyu_bridge_intervention_routes


def install_intervention_route_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls.turn_current = xinyu_bridge_intervention_routes.turn_current
    runtime_cls.turn_cancel = xinyu_bridge_intervention_routes.turn_cancel
    runtime_cls.turn_retry_lightweight = xinyu_bridge_intervention_routes.turn_retry_lightweight
    runtime_cls.turn_skip_sidecar = xinyu_bridge_intervention_routes.turn_skip_sidecar
    runtime_cls.turn_continue = xinyu_bridge_intervention_routes.turn_continue
    runtime_cls.turn_status_message = xinyu_bridge_intervention_routes.turn_status_message
