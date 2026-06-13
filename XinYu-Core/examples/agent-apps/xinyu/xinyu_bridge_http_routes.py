from __future__ import annotations

DESKTOP_GET_ROUTES = frozenset(
    {
        "/desktop/snapshot",
        "/desktop/events/recent",
        "/desktop/proactive/inbox",
        "/desktop/chat/recent",
        "/desktop/memory/recent",
        "/desktop/memory/growth-candidates",
        "/desktop/private-ecosystem/snapshot",
        "/desktop/private-browser/snapshot",
        "/desktop/private-desktop/snapshot",
        "/desktop/private-desktop/live-state",
        "/desktop/private-desktop/frame",
    }
)

EXTERNAL_GET_ROUTES = frozenset({"/external/plugins"})
TURN_GET_ROUTES = frozenset({"/turn/current"})
TURN_POST_ROUTES = frozenset(
    {
        "/turn/cancel",
        "/turn/retry-lightweight",
        "/turn/skip-sidecar",
        "/turn/continue",
        "/turn/status-message",
    }
)
PUBLIC_GET_ROUTES = frozenset({"/health"})
AUTHORIZED_GET_ROUTES = frozenset({"/probe", "/proactive"})

POST_ROUTES = frozenset(
    {
        "/chat",
        "/probe",
        "/proactive",
        "/proactive/ack",
        "/desktop/proactive/ack",
        "/desktop/self-action/approval",
        "/qq/outbox/claim",
        "/qq/outbox/ack",
        "/internal/message/ack",
        "/internal/message/drop",
        "/review/inbox/command",
        "/review/goldmark/mark_request",
        "/learning/ingest",
        "/learning/study",
        "/learning/observe",
        "/sticker/import",
        "/package/install",
        "/codex/execute",
        "/external/call",
        "/external/plugins/config",
        "/external/plugins/install",
        "/desktop/private-ecosystem/pause",
        "/desktop/private-ecosystem/grant",
        "/desktop/private-ecosystem/tick",
        "/desktop/private-browser/action",
        "/desktop/private-desktop/observe",
        "/desktop/private-desktop/start",
        "/desktop/private-desktop/stop",
    }
) | TURN_POST_ROUTES

TOKEN_REQUIRED_POST_ROUTES = frozenset(
    {
        "/codex/execute",
        "/package/install",
        "/qq/outbox/claim",
        "/qq/outbox/ack",
        "/internal/message/ack",
        "/internal/message/drop",
        "/review/inbox/command",
        "/review/goldmark/mark_request",
        "/sticker/import",
        "/external/call",
        "/external/plugins/config",
        "/external/plugins/install",
        "/desktop/private-ecosystem/pause",
        "/desktop/private-ecosystem/grant",
        "/desktop/private-ecosystem/tick",
        "/desktop/private-browser/action",
        "/desktop/private-desktop/observe",
        "/desktop/private-desktop/start",
        "/desktop/private-desktop/stop",
    }
)

LIFE_TICKET_PREFIX = "/life/metabolism/tickets"


def is_life_ticket_action_route(route: str) -> bool:
    if not route.startswith(f"{LIFE_TICKET_PREFIX}/"):
        return False
    parts = route.strip("/").split("/")
    return len(parts) == 5 and parts[:3] == ["life", "metabolism", "tickets"] and parts[4] in {
        "approve",
        "reject",
        "cancel",
    }


def life_ticket_action(route: str) -> tuple[str, str]:
    parts = route.strip("/").split("/")
    return parts[3], parts[4]


def is_life_ticket_get_route(route: str) -> bool:
    if route == LIFE_TICKET_PREFIX:
        return True
    if not route.startswith(f"{LIFE_TICKET_PREFIX}/"):
        return False
    parts = route.strip("/").split("/")
    return len(parts) == 4 and parts[:3] == ["life", "metabolism", "tickets"] and bool(parts[3])


def is_known_get_route(route: str) -> bool:
    return (
        route in PUBLIC_GET_ROUTES
        or route in AUTHORIZED_GET_ROUTES
        or route in DESKTOP_GET_ROUTES
        or route in EXTERNAL_GET_ROUTES
        or route in TURN_GET_ROUTES
        or is_life_ticket_get_route(route)
    )


def get_route_requires_auth(route: str) -> bool:
    return (
        route in AUTHORIZED_GET_ROUTES
        or route in DESKTOP_GET_ROUTES
        or route in EXTERNAL_GET_ROUTES
        or route in TURN_GET_ROUTES
        or is_life_ticket_get_route(route)
    )


def is_known_post_route(route: str) -> bool:
    return route in POST_ROUTES or is_life_ticket_action_route(route)


def post_route_requires_bridge_token(route: str) -> bool:
    return route in TOKEN_REQUIRED_POST_ROUTES or is_life_ticket_action_route(route)
