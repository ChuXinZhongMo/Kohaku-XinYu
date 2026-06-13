from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def prepared_finish_status(source: Mapping[str, Any]) -> tuple[Mapping[str, Any], Any, Any, Any]:
    return (
        source["pre_model_phase"],
        source["slow_live_entry"],
        source["model_turn_state"],
        source["post_model_state"],
    )


def runtime_renderer_status(runtime: Any) -> dict[str, Any]:
    return {
        "outward_renderer": runtime.outward_renderer,
        "renderer_mode": runtime.renderer_mode,
    }


__all__ = ["prepared_finish_status", "runtime_renderer_status"]
