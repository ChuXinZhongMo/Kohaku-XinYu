from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_http_dispatch_table import RuntimeRouteSpec


RunOnLoop = Callable[..., Any]


def invoke_runtime_spec(
    *,
    runtime: Any,
    payload: dict[str, Any],
    run_on_loop: RunOnLoop,
    request_timeout_seconds: int,
    spec: RuntimeRouteSpec,
) -> dict[str, Any]:
    if spec.fast_method:
        fast_call = getattr(runtime, spec.fast_method, None)
        if callable(fast_call):
            return fast_call(payload)
    runtime_call = getattr(runtime, spec.method)
    return run_on_loop(
        runtime_call(payload),
        timeout=spec.resolve_timeout(request_timeout_seconds),
    )
