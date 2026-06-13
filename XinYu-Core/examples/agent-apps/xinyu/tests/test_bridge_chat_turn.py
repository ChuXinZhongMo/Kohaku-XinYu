from __future__ import annotations

import asyncio
from http import HTTPStatus
from types import SimpleNamespace

import pytest

import xinyu_bridge_chat_turn as chat_turn
from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_chat_turn import run_chat_turn_after_request_with_trace
from xinyu_chat_service import ChatRequest, ChatServiceError, ChatTurnClock


def _trace(stage: str, **kwargs) -> None:
    del stage, kwargs


def test_run_chat_payload_rejects_closed_runtime() -> None:
    with pytest.raises(BridgeRequestError) as exc_info:
        asyncio.run(chat_turn.run_chat_payload(SimpleNamespace(_closed=True), {"text": "hello"}))

    assert exc_info.value.status is HTTPStatus.SERVICE_UNAVAILABLE
    assert exc_info.value.message == "bridge is shutting down"


def test_run_chat_payload_maps_chat_service_error() -> None:
    class ChatService:
        @staticmethod
        def prepare_request(*args, **kwargs):
            del args, kwargs
            raise ChatServiceError(HTTPStatus.BAD_REQUEST, "bad request")

    runtime = SimpleNamespace(
        _closed=False,
        chat_service=ChatService(),
        max_text_chars=10,
        _payload_text=lambda payload: payload.get("text", ""),
        _session_key=lambda payload: "session",
    )

    with pytest.raises(BridgeRequestError) as exc_info:
        asyncio.run(chat_turn.run_chat_payload(runtime, {"text": "hello"}))

    assert exc_info.value.status is HTTPStatus.BAD_REQUEST
    assert exc_info.value.message == "bad request"


def test_run_chat_payload_returns_empty_response_without_clock(monkeypatch) -> None:
    async def fail_after_request(*args, **kwargs):
        del args, kwargs
        raise AssertionError("empty response should skip turn orchestration")

    class ChatService:
        @staticmethod
        def prepare_request(*args, **kwargs):
            del args, kwargs
            return ChatRequest(
                payload={},
                text="",
                session_key="",
                empty_response={"accepted": True, "notes": ["empty_text"]},
            )

        @staticmethod
        def start_turn_clock():
            raise AssertionError("empty response should skip clock start")

    monkeypatch.setattr(chat_turn, "run_chat_turn_after_request_with_trace", fail_after_request)
    runtime = SimpleNamespace(
        _closed=False,
        chat_service=ChatService(),
        max_text_chars=10,
        _payload_text=lambda payload: payload.get("text", ""),
        _session_key=lambda payload: "session",
    )

    result = asyncio.run(chat_turn.run_chat_payload(runtime, {"text": ""}))

    assert result == {"accepted": True, "notes": ["empty_text"]}


def test_run_chat_payload_prepares_clock_and_event_time(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    async def fake_after_request(runtime_arg, payload_arg, **kwargs):
        calls.append(("after_request", {"runtime": runtime_arg, "payload": payload_arg, **kwargs}))
        return {"accepted": True, "reply": "ok"}

    class ChatService:
        @staticmethod
        def prepare_request(payload, **kwargs):
            calls.append(("prepare", {"payload": payload, **kwargs}))
            return ChatRequest(payload=payload, text="hello", session_key="qq:private:owner")

        @staticmethod
        def start_turn_clock():
            calls.append(("clock", {}))
            return ChatTurnClock(started_at=12.5, started_wall="2026-05-20T12:00:00+08:00")

    monkeypatch.setattr(chat_turn, "run_chat_turn_after_request_with_trace", fake_after_request)
    runtime = SimpleNamespace(
        _closed=False,
        chat_service=ChatService(),
        max_text_chars=10,
        _payload_text=lambda payload: payload.get("text", ""),
        _session_key=lambda payload: "session",
        _payload_event_time_iso=lambda payload, *, fallback: f"event:{fallback}",
        _payload_event_timestamp_seconds=lambda payload, *, fallback: fallback + 1,
    )

    result = asyncio.run(chat_turn.run_chat_payload(runtime, {"text": "hello"}))

    assert result == {"accepted": True, "reply": "ok"}
    assert [name for name, _ in calls] == ["prepare", "clock", "after_request"]
    assert calls[0][1]["max_text_chars"] == 10
    assert calls[2][1]["text"] == "hello"
    assert calls[2][1]["session_key"] == "qq:private:owner"
    assert calls[2][1]["turn_started_at"] == 12.5
    assert calls[2][1]["turn_started_wall"] == "2026-05-20T12:00:00+08:00"
    assert calls[2][1]["turn_event_time"] == "event:2026-05-20T12:00:00+08:00"
    assert calls[2][1]["turn_event_timestamp"] > 0


def test_run_chat_turn_after_request_returns_initial_fast_response(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    async def cleanup():
        calls.append(("cleanup", {}))
        return {"cleaned_sessions": 1}

    def fake_start(runtime, payload, **kwargs):
        calls.append(("start", {"runtime": runtime, "payload": payload, **kwargs}))
        return {"presence_start": {"turn_id": "turn-publish"}, "turn_id": "turn-1", "trace_route_stage": _trace}

    async def fake_initial(runtime, payload, **kwargs):
        calls.append(("initial", {"runtime": runtime, "payload": payload, **kwargs}))
        return {"response": {"accepted": True, "route": "fast"}, "desktop_started_published": True}

    async def fail_pre_model(*args, **kwargs):
        del args, kwargs
        raise AssertionError("initial fast response should skip pre-model phase")

    monkeypatch.setattr(chat_turn, "start_chat_turn_with_trace", fake_start)
    monkeypatch.setattr(chat_turn, "try_initial_semantic_fast_route_with_trace", fake_initial)
    monkeypatch.setattr(chat_turn, "run_pre_model_phase_with_trace", fail_pre_model)

    runtime = SimpleNamespace(
        _global_turn_lock=asyncio.Lock(),
        _cleanup_idle_sessions=cleanup,
        pre_model_routes_timeout_seconds=1.5,
        settle_seconds=0,
    )

    result = asyncio.run(
        run_chat_turn_after_request_with_trace(
            runtime,
            {"scope": "owner"},
            text="hello",
            session_key="qq:private:owner",
            turn_started_at=12.5,
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_event_time="2026-05-20T12:00:00+08:00",
            turn_event_timestamp=123,
        )
    )

    assert result == {"accepted": True, "route": "fast"}
    assert [name for name, _ in calls] == ["cleanup", "start", "initial"]
    assert calls[2][1]["cleanup"] == {"cleaned_sessions": 1}
    assert calls[2][1]["turn_id"] == "turn-1"


def test_run_chat_turn_after_request_falls_through_to_slow_live(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    async def cleanup():
        calls.append(("cleanup", {}))
        return {"cleaned_sessions": 0}

    def fake_start(runtime, payload, **kwargs):
        calls.append(("start", {"runtime": runtime, "payload": payload, **kwargs}))
        return {"presence_start": {"turn_id": "turn-publish"}, "turn_id": "turn-1", "trace_route_stage": _trace}

    async def fake_initial(runtime, payload, **kwargs):
        calls.append(("initial", {"runtime": runtime, "payload": payload, **kwargs}))
        return {"response": None, "desktop_started_published": False}

    async def fake_pre_model(runtime, payload, **kwargs):
        calls.append(("pre_model", {"runtime": runtime, "payload": payload, **kwargs}))
        return {
            "response": None,
            "before_memory": {"memory": "before"},
            "curiosity_eval": {"notes": ["curiosity"]},
            "event_sidecar": {"notes": ["event"]},
        }

    async def fake_slow_live(runtime, payload, **kwargs):
        calls.append(("slow_live", {"runtime": runtime, "payload": payload, **kwargs}))
        return {"accepted": True, "route": "slow_live"}

    monkeypatch.setattr(chat_turn, "start_chat_turn_with_trace", fake_start)
    monkeypatch.setattr(chat_turn, "try_initial_semantic_fast_route_with_trace", fake_initial)
    monkeypatch.setattr(chat_turn, "run_pre_model_phase_with_trace", fake_pre_model)
    monkeypatch.setattr(chat_turn, "run_slow_live_turn_from_pre_model_phase_with_trace", fake_slow_live)

    runtime = SimpleNamespace(
        _global_turn_lock=asyncio.Lock(),
        _cleanup_idle_sessions=cleanup,
        pre_model_routes_timeout_seconds=2.5,
        settle_seconds=0.25,
    )

    result = asyncio.run(
        run_chat_turn_after_request_with_trace(
            runtime,
            {"scope": "owner"},
            text="hello",
            session_key="qq:private:owner",
            turn_started_at=12.5,
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_event_time="2026-05-20T12:00:00+08:00",
            turn_event_timestamp=123,
        )
    )

    assert result == {"accepted": True, "route": "slow_live"}
    assert [name for name, _ in calls] == ["cleanup", "start", "initial", "pre_model", "slow_live"]
    assert calls[3][1]["desktop_started_published"] is False
    assert calls[3][1]["timeout_seconds"] == 2.5
    assert calls[4][1]["turn_id"] == "turn-1"
    assert calls[4][1]["publish_turn_id"] == "turn-publish"
    assert calls[4][1]["turn_event_timestamp"] == 123
    assert calls[4][1]["settle_seconds"] == 0.25
