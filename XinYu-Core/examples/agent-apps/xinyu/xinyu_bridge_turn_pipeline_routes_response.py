from __future__ import annotations

from typing import Any

from xinyu_bridge_runtime_repair_status_route import (
    looks_like_runtime_repair_status_question as _runtime_looks_like_runtime_repair_status_question,
    maybe_handle_runtime_repair_status_turn as _runtime_maybe_handle_runtime_repair_status_turn,
    tcp_connect as _runtime_tcp_connect,
)
from xinyu_bridge_tinykernel_shadow_route import run_tinykernel_shadow as _runtime_run_tinykernel_shadow


async def run_tinykernel_shadow_response(
    runtime: Any,
    payload: dict[str, Any],
    *,
    route_payload: dict[str, Any],
    deps: dict[str, Any],
) -> dict[str, Any]:
    return await _runtime_run_tinykernel_shadow(runtime, payload, **route_payload, **deps)


async def maybe_runtime_repair_status_response(
    runtime: Any,
    payload: dict[str, Any],
    *,
    route_payload: dict[str, Any],
    deps: dict[str, Any],
) -> dict[str, Any] | None:
    return await _runtime_maybe_handle_runtime_repair_status_turn(runtime, payload, **route_payload, **deps)


def looks_like_runtime_repair_status_question(text: str) -> bool:
    return _runtime_looks_like_runtime_repair_status_question(text)


def tcp_connect(host: str, port: int, timeout: float = 0.5) -> bool:
    return _runtime_tcp_connect(host, port, timeout=timeout)


__all__ = [
    "looks_like_runtime_repair_status_question",
    "maybe_runtime_repair_status_response",
    "run_tinykernel_shadow_response",
    "tcp_connect",
]
