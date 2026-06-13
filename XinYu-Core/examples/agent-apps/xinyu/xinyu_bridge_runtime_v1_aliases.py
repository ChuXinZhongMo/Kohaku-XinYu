from __future__ import annotations

from typing import Any

import xinyu_bridge_v1_routes

V1_OWNER_SIMPLE_CANARY_ENV = xinyu_bridge_v1_routes.V1_OWNER_SIMPLE_CANARY_ENV
V1_CANARY_GREETING_TEXTS = xinyu_bridge_v1_routes.V1_CANARY_GREETING_TEXTS
V1_CANARY_ACK_TEXTS = xinyu_bridge_v1_routes.V1_CANARY_ACK_TEXTS


def install_v1_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls._v1_health = xinyu_bridge_v1_routes.health
    runtime_cls._ensure_v1_app = xinyu_bridge_v1_routes.ensure_app
    runtime_cls._record_v1_shadow_readiness = xinyu_bridge_v1_routes.record_shadow_readiness
    runtime_cls._run_v1_shadow = xinyu_bridge_v1_routes.run_shadow
    runtime_cls._v1_canary_payload_allowed = xinyu_bridge_v1_routes.canary_payload_allowed
    runtime_cls._maybe_handle_v1_canary_turn = xinyu_bridge_v1_routes.handle_canary_turn
