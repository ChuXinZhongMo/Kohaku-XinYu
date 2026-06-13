from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_http_dispatch_paths import life_ticket_child_id
from xinyu_bridge_http_dispatch_payload import attach_life_ticket_id
from xinyu_bridge_http_dispatch_table import LIFE_TICKET_ACTION_METHODS, RuntimeRouteSpec
from xinyu_bridge_http_routes import LIFE_TICKET_PREFIX


def life_ticket_get_spec(route: str, payload: dict[str, Any]) -> RuntimeRouteSpec | None:
    if route == LIFE_TICKET_PREFIX:
        return RuntimeRouteSpec("life_metabolism_ticket_list", 5)

    ticket_id = life_ticket_child_id(route, prefix=LIFE_TICKET_PREFIX)
    if ticket_id is None:
        return None
    attach_life_ticket_id(payload, ticket_id)
    return RuntimeRouteSpec("life_metabolism_ticket_get", 5)


def life_ticket_post_spec(
    route: str,
    payload: dict[str, Any],
    *,
    is_action_route_func: Callable[[str], bool],
    action_func: Callable[[str], tuple[str, str]],
) -> RuntimeRouteSpec | None:
    if not is_action_route_func(route):
        return None
    ticket_id, action = action_func(route)
    attach_life_ticket_id(payload, ticket_id)
    method = LIFE_TICKET_ACTION_METHODS.get(
        action,
        LIFE_TICKET_ACTION_METHODS["cancel"],
    )
    return RuntimeRouteSpec(method, 10)
