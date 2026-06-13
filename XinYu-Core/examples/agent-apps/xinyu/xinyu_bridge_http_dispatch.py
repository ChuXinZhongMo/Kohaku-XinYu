from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable

from xinyu_bridge_http_dispatch_life_ticket import life_ticket_get_spec, life_ticket_post_spec
from xinyu_bridge_http_dispatch_payload import ensure_proactive_claim_default
from xinyu_bridge_http_dispatch_response import (
    BridgeHTTPDispatchResult,
    status_from_result_http_status,
)
from xinyu_bridge_http_dispatch_table import (
    GET_ROUTE_DISPATCH,
    POST_ROUTE_DISPATCH,
)
from xinyu_bridge_http_routes import is_life_ticket_action_route, life_ticket_action
from xinyu_bridge_http_runtime_invoker import invoke_runtime_spec

RunOnLoop = Callable[..., Any]

CODEX_EXECUTION_HTTP_DISPATCH_MARKERS = ("/codex/execute", "runtime.codex_execute")


def dispatch_get_route(
    *,
    runtime: Any,
    route: str,
    payload: dict[str, Any],
    run_on_loop: RunOnLoop,
) -> dict[str, Any] | None:
    if route == "/health":
        health_snapshot = getattr(runtime, "health_snapshot", None)
        if callable(health_snapshot):
            return health_snapshot()
        return run_on_loop(runtime.health(), timeout=10)

    spec = GET_ROUTE_DISPATCH.get(route)
    if spec is not None:
        if route == "/proactive":
            ensure_proactive_claim_default(payload)
        return invoke_runtime_spec(
            runtime=runtime,
            payload=payload,
            run_on_loop=run_on_loop,
            request_timeout_seconds=0,
            spec=spec,
        )

    spec = life_ticket_get_spec(route, payload)
    if spec is not None:
        return invoke_runtime_spec(
            runtime=runtime,
            payload=payload,
            run_on_loop=run_on_loop,
            request_timeout_seconds=0,
            spec=spec,
        )

    return None


def dispatch_post_route(
    *,
    runtime: Any,
    route: str,
    payload: dict[str, Any],
    run_on_loop: RunOnLoop,
    request_timeout_seconds: int,
) -> BridgeHTTPDispatchResult | None:
    spec = life_ticket_post_spec(
        route,
        payload,
        is_action_route_func=is_life_ticket_action_route,
        action_func=life_ticket_action,
    )
    if spec is None:
        spec = POST_ROUTE_DISPATCH.get(route)
        if spec is None:
            return None

    result = invoke_runtime_spec(
        runtime=runtime,
        payload=payload,
        run_on_loop=run_on_loop,
        request_timeout_seconds=request_timeout_seconds,
        spec=spec,
    )
    if spec.status_from_http_status:
        return BridgeHTTPDispatchResult(
            data=result,
            status=status_from_result_http_status(result, status_cls=HTTPStatus),
        )
    return BridgeHTTPDispatchResult(data=result)
