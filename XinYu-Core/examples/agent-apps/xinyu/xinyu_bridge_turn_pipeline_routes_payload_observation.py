from __future__ import annotations

from typing import Any


def build_observation_payload(
    *,
    text: str,
    session_key: str,
    trace_route_stage: Any,
    observed_at: str | None,
) -> dict[str, Any]:
    return {
        "text": text,
        "session_key": session_key,
        "trace_route_stage": trace_route_stage,
        "observed_at": observed_at,
    }


__all__ = ["build_observation_payload"]
