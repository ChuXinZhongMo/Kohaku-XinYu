from __future__ import annotations

from typing import Any

from xinyu_bridge_turn_pipeline_facade_bindings import (
    FACADE_EXPORTS as _FACADE_EXPORTS,
    export_facade_namespace,
)
from xinyu_bridge_turn_pipeline_facade_decisions import bind_decision_facade
from xinyu_bridge_turn_pipeline_facade_entry import bind_entry_facade
from xinyu_bridge_turn_pipeline_facade_routes import bind_route_facade


def bind_turn_pipeline_facade(hooks: Any) -> dict[str, Any]:
    exports: dict[str, Any] = {}
    for bind_group in (
        bind_entry_facade,
        bind_decision_facade,
        bind_route_facade,
    ):
        exports.update(bind_group(hooks))
    return export_facade_namespace(hooks, exports)
