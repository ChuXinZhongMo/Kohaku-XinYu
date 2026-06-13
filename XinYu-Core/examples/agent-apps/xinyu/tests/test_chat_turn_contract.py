from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from xinyu_bridge_chat_turn_contract import (
    CHAT_TURN_FALLBACK_ADAPTER,
    CHAT_TURN_PROCESS_SPLIT_ALLOWED,
    CHAT_TURN_PROTECTED_MODULES,
    CHAT_TURN_ROLLBACK,
    CHAT_TURN_STATE_OWNER,
    ChatTurnHarness,
    chat_turn_capabilities,
    chat_turn_control_plane_routes,
    chat_turn_execution_routes,
    chat_turn_routes,
    chat_turn_runtime_methods,
    chat_turn_token_required_routes,
)
from xinyu_bridge_http_dispatch_table import POST_ROUTE_DISPATCH
from xinyu_bridge_http_routes import is_known_post_route, post_route_requires_bridge_token
from xinyu_chat_service import build_chat_service
from xinyu_serviceization_contracts import service_contract_by_id


ROOT = Path(__file__).resolve().parents[1]


def test_chat_turn_contract_matches_service_boundary_manifest() -> None:
    contract = service_contract_by_id("chat_turn")
    capabilities = chat_turn_capabilities()

    assert chat_turn_routes() == contract.api_routes
    assert chat_turn_runtime_methods() == contract.runtime_facade_methods
    assert chat_turn_execution_routes() == ("/chat",)
    assert chat_turn_control_plane_routes() == contract.api_routes[1:]
    assert chat_turn_token_required_routes() == (
        "/internal/message/ack",
        "/internal/message/drop",
    )
    assert contract.process_split_candidate is False
    assert CHAT_TURN_PROCESS_SPLIT_ALLOWED is False
    assert {capability.kind for capability in capabilities} == {
        "execution",
        "message_feedback",
        "turn_control",
    }


def test_chat_turn_contract_matches_http_dispatch_table() -> None:
    for capability in chat_turn_capabilities():
        assert capability.http_method == "POST"
        assert is_known_post_route(capability.route)
        assert post_route_requires_bridge_token(capability.route) is capability.requires_bridge_token
        assert POST_ROUTE_DISPATCH[capability.route].method == capability.runtime_method


def test_chat_turn_contract_protected_modules_exist() -> None:
    for module in CHAT_TURN_PROTECTED_MODULES:
        assert (ROOT / module).exists()


def test_chat_turn_contract_keeps_chat_service_as_request_preparer() -> None:
    service = build_chat_service()
    request = service.prepare_request(
        {"text": "hello", "session_id": "session-1"},
        max_text_chars=10,
        payload_text=lambda payload: str(payload.get("text") or "").strip(),
        session_key=lambda payload: str(payload.get("session_id") or ""),
    )

    assert request.text == "hello"
    assert request.session_key == "session-1"
    assert request.empty_response is None


def test_chat_turn_harness_lifecycle_readiness_and_fallback() -> None:
    harness = ChatTurnHarness()

    initial = harness.readiness()
    assert initial.service_id == "chat_turn"
    assert initial.mode == "in_process"
    assert initial.started is False
    assert initial.ready is False
    assert initial.api_routes == chat_turn_routes()
    assert initial.runtime_facade_methods == chat_turn_runtime_methods()
    assert initial.execution_routes == ("/chat",)
    assert initial.control_plane_routes == chat_turn_control_plane_routes()
    assert initial.token_required_routes == chat_turn_token_required_routes()
    assert initial.state_owner == CHAT_TURN_STATE_OWNER
    assert initial.fallback_adapter == CHAT_TURN_FALLBACK_ADAPTER
    assert initial.rollback == CHAT_TURN_ROLLBACK
    assert "runtime_chat_method_remains_monkeypatchable" in initial.notes
    assert "control_plane_routes_remain_in_process" in initial.notes

    started = harness.start()
    assert started.started is True
    assert started.ready is True

    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def _method(name: str):
        def call(*args: object, **kwargs: object) -> dict[str, object]:
            calls.append((args, kwargs))
            return {"method": name, "args": args, "kwargs": kwargs}

        return call

    def chat(*args: object, **kwargs: object) -> dict[str, object]:
        calls.append((args, kwargs))
        return {"method": "chat", "args": args, "kwargs": kwargs}

    runtime = SimpleNamespace(
        chat=chat,
        **{
            method: _method(method)
            for method in chat_turn_runtime_methods()
            if method != "chat"
        },
    )
    fallback = harness.fallback_adapter(runtime)

    assert set(fallback) == set(chat_turn_runtime_methods())
    assert fallback["chat"]({"text": "hello"}, trace=True) == {
        "method": "chat",
        "args": ({"text": "hello"},),
        "kwargs": {"trace": True},
    }
    assert calls == [(({"text": "hello"},), {"trace": True})]

    stopped = harness.stop()
    assert stopped.started is False
    assert stopped.ready is False
