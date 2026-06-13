from __future__ import annotations

import xinyu_bridge_http
import xinyu_bridge_http_routes as routes
from xinyu_bridge_http_routes import (
    LIFE_TICKET_PREFIX,
    get_route_requires_auth,
    is_known_get_route,
    is_known_post_route,
    is_life_ticket_action_route,
    life_ticket_action,
    post_route_requires_bridge_token,
)


def test_get_route_contract_separates_public_and_authorized_routes() -> None:
    assert is_known_get_route("/health")
    assert not get_route_requires_auth("/health")

    for route in (
        "/probe",
        "/proactive",
        "/desktop/private-desktop/frame",
        "/external/plugins",
        "/turn/current",
        LIFE_TICKET_PREFIX,
        f"{LIFE_TICKET_PREFIX}/ticket-1",
    ):
        assert is_known_get_route(route)
        assert get_route_requires_auth(route)

    assert not is_known_get_route("/missing")
    assert not is_known_get_route(f"{LIFE_TICKET_PREFIX}/ticket-1/approve")
    assert not is_known_get_route(f"{LIFE_TICKET_PREFIX}/ticket-1/extra/segment")


def test_post_route_contract_tracks_token_required_operations() -> None:
    assert is_known_post_route("/chat")
    assert not post_route_requires_bridge_token("/chat")

    assert is_known_post_route("/probe")
    assert not post_route_requires_bridge_token("/probe")

    assert is_known_post_route("/turn/continue")
    assert not post_route_requires_bridge_token("/turn/continue")

    for route in (
        "/codex/execute",
        "/package/install",
        "/desktop/private-ecosystem/tick",
        "/desktop/private-browser/action",
        "/desktop/private-desktop/start",
    ):
        assert is_known_post_route(route)
        assert post_route_requires_bridge_token(route)

    assert not is_known_post_route("/missing")


def test_token_required_post_routes_are_pinned_for_service_boundaries() -> None:
    expected = {
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

    assert routes.TOKEN_REQUIRED_POST_ROUTES == expected
    assert all(is_known_post_route(route) for route in expected)
    assert all(post_route_requires_bridge_token(route) for route in expected)


def test_authorized_get_routes_are_pinned_for_service_boundaries() -> None:
    expected_authorized = (
        routes.AUTHORIZED_GET_ROUTES
        | routes.DESKTOP_GET_ROUTES
        | routes.EXTERNAL_GET_ROUTES
        | routes.TURN_GET_ROUTES
        | {LIFE_TICKET_PREFIX, f"{LIFE_TICKET_PREFIX}/ticket-1"}
    )

    assert not get_route_requires_auth("/health")
    assert all(is_known_get_route(route) for route in expected_authorized)
    assert all(get_route_requires_auth(route) for route in expected_authorized)


def test_life_ticket_route_contract_accepts_only_supported_shapes() -> None:
    approve_route = f"{LIFE_TICKET_PREFIX}/ticket-1/approve"
    assert is_known_post_route(approve_route)
    assert is_life_ticket_action_route(approve_route)
    assert post_route_requires_bridge_token(approve_route)
    assert life_ticket_action(approve_route) == ("ticket-1", "approve")

    for route in (
        f"{LIFE_TICKET_PREFIX}/ticket-1/reject",
        f"{LIFE_TICKET_PREFIX}/ticket-1/cancel",
    ):
        assert is_life_ticket_action_route(route)
        assert post_route_requires_bridge_token(route)

    assert not is_life_ticket_action_route(f"{LIFE_TICKET_PREFIX}/ticket-1/hold")
    assert not is_life_ticket_action_route(f"{LIFE_TICKET_PREFIX}/ticket-1/approve/trailing")
    assert not post_route_requires_bridge_token(f"{LIFE_TICKET_PREFIX}/ticket-1/hold")
    assert not post_route_requires_bridge_token(f"{LIFE_TICKET_PREFIX}/ticket-1/approve/trailing")


def test_bridge_http_preserves_legacy_route_constant_exports() -> None:
    assert xinyu_bridge_http.DESKTOP_GET_ROUTES is routes.DESKTOP_GET_ROUTES
    assert xinyu_bridge_http.EXTERNAL_GET_ROUTES is routes.EXTERNAL_GET_ROUTES
    assert xinyu_bridge_http.TURN_GET_ROUTES is routes.TURN_GET_ROUTES
    assert xinyu_bridge_http.TURN_POST_ROUTES is routes.TURN_POST_ROUTES
    assert xinyu_bridge_http.LIFE_TICKET_PREFIX == routes.LIFE_TICKET_PREFIX
