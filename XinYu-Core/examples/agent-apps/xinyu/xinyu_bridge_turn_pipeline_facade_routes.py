from __future__ import annotations

from typing import Any

from xinyu_bridge_turn_pipeline_facade_routes_pre_model import bind_pre_model_route_facade
from xinyu_bridge_turn_pipeline_facade_routes_runtime_repair import bind_runtime_repair_route_facade
from xinyu_bridge_turn_pipeline_facade_routes_tinykernel import bind_tinykernel_route_facade


def bind_route_facade(hooks: Any) -> dict[str, Any]:
    exports: dict[str, Any] = {}
    for bind_group in (
        bind_pre_model_route_facade,
        bind_tinykernel_route_facade,
        bind_runtime_repair_route_facade,
    ):
        exports.update(bind_group(hooks))
    return exports
