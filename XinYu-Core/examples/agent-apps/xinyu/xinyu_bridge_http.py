from __future__ import annotations

from xinyu_bridge_http_dispatch import BridgeHTTPDispatchResult, dispatch_get_route, dispatch_post_route
from xinyu_bridge_http_handler import XinYuBridgeRequestHandler
from xinyu_bridge_http_io import BridgeHTTPRequestError
from xinyu_bridge_http_routes import (
    DESKTOP_GET_ROUTES,
    EXTERNAL_GET_ROUTES,
    LIFE_TICKET_PREFIX,
    TURN_GET_ROUTES,
    TURN_POST_ROUTES,
    get_route_requires_auth,
    is_known_get_route,
    is_known_post_route,
    is_life_ticket_action_route,
    is_life_ticket_get_route,
    life_ticket_action,
    post_route_requires_bridge_token,
)
from xinyu_bridge_http_server import XinYuBridgeHTTPServer


_BridgeHTTPRequestError = BridgeHTTPRequestError
