from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from xinyu_bridge_v1_payloads import safe_str, shadow_payload


def record_shadow_readiness_impl(
    runtime: Any,
    shadow_payload_in: dict[str, Any],
    *,
    accepted: bool,
    route: str,
    trace_id: str,
    elapsed_ms: int,
    error: str = "",
    record_observation_func: Callable[..., dict[str, Any]],
    safe_str_func: Callable[[Any], str] = safe_str,
) -> list[str]:
    try:
        readiness = record_observation_func(
            runtime.xinyu_dir,
            accepted=accepted,
            route=route,
            trace_id=trace_id,
            elapsed_ms=elapsed_ms,
            error=error,
            payload=shadow_payload_in,
        )
    except Exception as exc:
        return [f"v1_canary_readiness_error:{type(exc).__name__}"]
    notes = readiness.get("notes") if isinstance(readiness, dict) else []
    if not isinstance(notes, list):
        return []
    return [safe_str_func(note) for note in notes[:4]]


async def run_shadow_impl(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    ensure_app_func: Callable[[Any], Any],
    record_shadow_readiness_func: Callable[..., list[str]],
    safe_str_func: Callable[[Any], str] = safe_str,
) -> dict[str, Any]:
    if not runtime.v1_shadow_mode:
        return {"notes": []}
    started = time.monotonic()
    shadow_payload_in: dict[str, Any] = {}
    try:
        app = ensure_app_func(runtime)
        shadow_payload_in = shadow_payload(runtime, payload, text=text, safe_str_func=safe_str_func)
        reply = await asyncio.wait_for(
            app.shadow_payload(shadow_payload_in),
            timeout=runtime.v1_shadow_timeout_seconds,
        )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        runtime._v1_last_error = ""
        runtime._v1_last_trace_id = reply.trace_id
        runtime._v1_last_route = reply.route
        readiness_notes = record_shadow_readiness_func(
            runtime,
            shadow_payload_in,
            accepted=reply.accepted,
            route=reply.route,
            trace_id=reply.trace_id,
            elapsed_ms=elapsed_ms,
        )
        return {
            "accepted": reply.accepted,
            "route": reply.route,
            "trace_id": reply.trace_id,
            "elapsed_ms": elapsed_ms,
            "notes": [
                f"v1_shadow_route:{reply.route or 'unknown'}",
                f"v1_shadow_elapsed_ms:{elapsed_ms}",
                *readiness_notes,
            ],
        }
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        runtime._v1_last_error = f"{type(exc).__name__}: {exc}"
        print(f"[xinyu_core_bridge] v1 shadow failed: {runtime._v1_last_error}", flush=True)
        readiness_notes = record_shadow_readiness_func(
            runtime,
            shadow_payload_in if shadow_payload_in else dict(payload),
            accepted=False,
            route="",
            trace_id="",
            elapsed_ms=elapsed_ms,
            error=f"{type(exc).__name__}: {exc}",
        )
        return {
            "accepted": False,
            "route": "",
            "trace_id": "",
            "elapsed_ms": elapsed_ms,
            "notes": [f"v1_shadow_error:{type(exc).__name__}", *readiness_notes],
        }
