from __future__ import annotations

from typing import Any

import xinyu_bridge_turn_pipeline_routes as _routes


def bind_tinykernel_route_facade(hooks: Any) -> dict[str, Any]:
    async def _run_tinykernel_shadow(
        runtime: Any,
        payload: dict[str, Any],
        *,
        text: str,
        turn_id: str,
        observed_at: str,
    ) -> dict[str, Any]:
        return await _routes.run_tinykernel_shadow(
            hooks,
            runtime,
            payload,
            text=text,
            turn_id=turn_id,
            observed_at=observed_at,
        )

    return {"_run_tinykernel_shadow": _run_tinykernel_shadow}


__all__ = ["bind_tinykernel_route_facade"]
