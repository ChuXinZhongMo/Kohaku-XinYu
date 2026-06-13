from __future__ import annotations

from collections.abc import Callable
from typing import Any

import xinyu_bridge_semantic_fast_routes
from xinyu_bridge_reply_pipeline import render_outward_reply_with_trace
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_bridge_slow_live_reply_dedupe import apply_slow_live_visible_dedupe
from xinyu_bridge_slow_live_reply_pipeline_bindings import apply_slow_live_reply_adjustment_pipeline
from xinyu_bridge_slow_live_reply_policy import apply_slow_live_life_reply_policy
from xinyu_bridge_slow_live_reply_repair_bindings import apply_slow_live_current_reference_repair
from xinyu_bridge_slow_live_reply_repair_bindings import apply_slow_live_stale_context_repair
from xinyu_bridge_slow_live_reply_rendering_bindings import apply_slow_live_final_reply_guard
from xinyu_bridge_slow_live_reply_rendering_bindings import apply_slow_live_outward_renderer
from xinyu_bridge_slow_live_reply_shape import FALSE_SINGLE_BUBBLE_REPLY
from xinyu_bridge_slow_live_reply_shape import STYLE_PRESSURE_EMPTY_REPLY
from xinyu_bridge_slow_live_reply_shape_bindings import apply_slow_live_reply_bubble_policy
from xinyu_bridge_slow_live_reply_shape_bindings import apply_slow_live_style_pressure_empty_fallback
from xinyu_bridge_slow_live_reply_shape_bindings import recover_slow_live_empty_visible_reply
from xinyu_bridge_slow_live_reply_sticker_bindings import apply_slow_live_sticker_reply_override
from xinyu_current_reference_guard import repair_current_reference_reply
from xinyu_expression_self_learning import record_expression_self_learning_event
from xinyu_life_reply_policy import apply_life_reply_policy
from xinyu_visible_reply_guard import dedupe_visible_reply


TraceRouteStage = Callable[..., Any]


__all__ = (
    "Any",
    "Callable",
    "FALSE_SINGLE_BUBBLE_REPLY",
    "STYLE_PRESSURE_EMPTY_REPLY",
    "TraceRouteStage",
    "apply_life_reply_policy",
    "apply_slow_live_current_reference_repair",
    "apply_slow_live_final_reply_guard",
    "apply_slow_live_life_reply_policy",
    "apply_slow_live_outward_renderer",
    "apply_slow_live_reply_adjustment_pipeline",
    "apply_slow_live_reply_bubble_policy",
    "apply_slow_live_stale_context_repair",
    "apply_slow_live_sticker_reply_override",
    "apply_slow_live_style_pressure_empty_fallback",
    "apply_slow_live_visible_dedupe",
    "dedupe_visible_reply",
    "normalize_bridge_reply",
    "record_expression_self_learning_event",
    "render_outward_reply_with_trace",
    "repair_current_reference_reply",
    "recover_slow_live_empty_visible_reply",
    "xinyu_bridge_semantic_fast_routes",
)
