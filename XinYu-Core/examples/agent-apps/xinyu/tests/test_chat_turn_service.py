from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_chat_turn_contract import (
    CHAT_TURN_FALLBACK_ADAPTER,
    CHAT_TURN_ROLLBACK,
    CHAT_TURN_STATE_OWNER,
    chat_turn_control_plane_routes,
    chat_turn_execution_routes,
    chat_turn_routes,
    chat_turn_runtime_methods,
    chat_turn_token_required_routes,
)
from xinyu_bridge_chat_turn_service import (
    CHAT_TURN_SERVICE_MODE_LOCAL,
    build_chat_turn_service_handle,
    chat_turn_service_readiness,
)


class _ChatService:
    def prepare_request(self) -> None:
        return None

    def start_turn_clock(self) -> None:
        return None


def test_chat_turn_service_default_readiness_is_local_only_and_not_started() -> None:
    runtime = SimpleNamespace(chat=lambda payload: payload, chat_service=_ChatService())
    handle = build_chat_turn_service_handle()

    readiness = handle.readiness(runtime)

    assert readiness.service_id == "chat_turn"
    assert readiness.mode == CHAT_TURN_SERVICE_MODE_LOCAL
    assert readiness.started is False
    assert readiness.ready is False
    assert readiness.local_only is True
    assert readiness.process_split_candidate is False
    assert readiness.process_split_ready is False
    assert readiness.runtime_method_available is True
    assert readiness.chat_service_available is True
    assert readiness.api_routes == chat_turn_routes()
    assert readiness.runtime_facade_methods == chat_turn_runtime_methods()
    assert readiness.execution_routes == chat_turn_execution_routes()
    assert readiness.control_plane_routes == chat_turn_control_plane_routes()
    assert readiness.token_required_routes == chat_turn_token_required_routes()
    assert readiness.state_owner == CHAT_TURN_STATE_OWNER
    assert readiness.fallback_adapter == CHAT_TURN_FALLBACK_ADAPTER
    assert readiness.rollback == CHAT_TURN_ROLLBACK
    assert "chat_execution_path_unchanged" in readiness.notes
    assert "control_plane_routes_remain_in_process" in readiness.notes


def test_chat_turn_service_lifecycle_does_not_install_backend_or_replace_chat() -> None:
    calls: list[dict[str, object]] = []

    def chat(payload: dict[str, object]) -> dict[str, object]:
        calls.append(payload)
        return {"reply": "ok"}

    runtime = SimpleNamespace(chat=chat, chat_service=_ChatService())
    handle = build_chat_turn_service_handle()

    started = handle.start(runtime)
    result = runtime.chat({"text": "hello"})
    closed = handle.close(runtime)

    assert started.ready is True
    assert result == {"reply": "ok"}
    assert calls == [{"text": "hello"}]
    assert closed.started is False
    assert closed.ready is False
    assert runtime.chat is chat


def test_chat_turn_service_reports_missing_runtime_or_chat_service() -> None:
    runtime = SimpleNamespace(chat_service=SimpleNamespace(prepare_request=lambda: None))
    handle = build_chat_turn_service_handle()

    readiness = handle.start(runtime)

    assert readiness.ready is False
    assert readiness.runtime_method_available is False
    assert readiness.chat_service_available is False


def test_chat_turn_service_readiness_helper_uses_runtime_handle() -> None:
    runtime = SimpleNamespace(chat=lambda payload: payload, chat_service=_ChatService())
    runtime._chat_turn_service = build_chat_turn_service_handle()
    runtime._chat_turn_service.start(runtime)

    assert chat_turn_service_readiness(runtime).ready is True
