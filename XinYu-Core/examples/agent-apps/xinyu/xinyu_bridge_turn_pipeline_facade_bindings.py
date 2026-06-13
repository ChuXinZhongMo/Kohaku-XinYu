from __future__ import annotations

from collections.abc import Mapping
from typing import Any


FACADE_EXPORTS = (
    "_safe_str",
    "_timestamp_or_now_iso",
    "start_chat_turn_with_trace",
    "capture_memory_snapshot_with_trace",
    "publish_chat_started_with_trace",
    "probe_semantic_fast_decision_with_trace",
    "try_pre_slow_semantic_fast_route_with_trace",
    "try_initial_semantic_fast_route_with_trace",
    "run_pre_model_phase_with_trace",
    "run_pre_model_observation_sidecars_with_trace",
    "run_pre_model_routes_with_timeout",
    "run_pre_model_routes",
    "_run_tinykernel_shadow",
    "_maybe_handle_runtime_repair_status_turn",
    "_looks_like_runtime_repair_status_question",
    "_tcp_connect",
)


def export_facade_namespace(hooks: Any, exports: Mapping[str, Any]) -> dict[str, Any]:
    facade_exports = {name: exports[name] for name in FACADE_EXPORTS}
    for name, value in facade_exports.items():
        value.__module__ = hooks.__name__
        value.__qualname__ = name
    return facade_exports
