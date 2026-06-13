from __future__ import annotations

import asyncio
from types import SimpleNamespace

import xinyu_bridge_desktop_events
import xinyu_bridge_desktop_event_tts


class _Done:
    def __init__(self, exc: Exception | None = None) -> None:
        self.exc = exc

    def result(self) -> dict[str, object]:
        if self.exc is not None:
            raise self.exc
        return {"ok": True}


class _Future:
    def __init__(self, done: _Done) -> None:
        self.done = done
        self.callback_called = False

    def add_done_callback(self, callback) -> None:
        self.callback_called = True
        callback(self.done)


def test_desktop_publish_event_delegates_to_runtime_event_bus() -> None:
    calls: list[tuple[str, dict[str, object], dict[str, object]]] = []

    class _EventBus:
        async def publish(self, event_type: str, payload: dict[str, object], **kwargs) -> dict[str, object]:
            calls.append((event_type, payload, kwargs))
            return {"id": "event-1"}

    result = asyncio.run(
        xinyu_bridge_desktop_events.desktop_publish_event(
            SimpleNamespace(desktop_event_bus=_EventBus()),
            "chat.turn.started",
            {"turnId": "turn-1"},
            privacy="owner_private",
            severity="warn",
        )
    )

    assert result == {"id": "event-1"}
    assert calls == [
        (
            "chat.turn.started",
            {"turnId": "turn-1"},
            {"source": "xinyu_core_bridge", "privacy": "owner_private", "severity": "warn"},
        )
    ]


def test_desktop_publish_event_handles_missing_bus_and_errors(capsys) -> None:
    class _FailingEventBus:
        async def publish(self, *args, **kwargs) -> dict[str, object]:
            raise RuntimeError("publish failed")

    assert asyncio.run(
        xinyu_bridge_desktop_events.desktop_publish_event(
            SimpleNamespace(desktop_event_bus=None),
            "event.missing",
            {},
        )
    ) == {}
    assert asyncio.run(
        xinyu_bridge_desktop_events.desktop_publish_event(
            SimpleNamespace(desktop_event_bus=_FailingEventBus()),
            "event.failed",
            {},
        )
    ) == {}

    assert "[xinyu_core_bridge] desktop event publish failed: event.failed: publish failed" in capsys.readouterr().out


def test_desktop_publish_event_threadsafe_delegates_and_logs_callback_failure(capsys) -> None:
    calls: list[tuple[str, dict[str, object], dict[str, object]]] = []
    future = _Future(_Done(RuntimeError("callback failed")))

    class _EventBus:
        def publish_threadsafe(self, event_type: str, payload: dict[str, object], **kwargs) -> _Future:
            calls.append((event_type, payload, kwargs))
            return future

    xinyu_bridge_desktop_events.desktop_publish_event_threadsafe(
        SimpleNamespace(desktop_event_bus=_EventBus()),
        "proactive.candidate.ready",
        {"candidateId": "candidate-1"},
        privacy="owner_private",
        severity="error",
    )

    assert calls == [
        (
            "proactive.candidate.ready",
            {"candidateId": "candidate-1"},
            {"source": "xinyu_core_bridge", "privacy": "owner_private", "severity": "error"},
        )
    ]
    assert future.callback_called is True
    assert (
        "[xinyu_core_bridge] desktop event publish failed: proactive.candidate.ready: callback failed"
        in capsys.readouterr().out
    )


def test_desktop_publish_event_threadsafe_handles_missing_bus_and_scheduling_errors(capsys) -> None:
    class _FailingEventBus:
        def publish_threadsafe(self, *args, **kwargs) -> _Future:
            raise RuntimeError("schedule failed")

    xinyu_bridge_desktop_events.desktop_publish_event_threadsafe(
        SimpleNamespace(desktop_event_bus=None),
        "event.missing",
        {},
    )
    xinyu_bridge_desktop_events.desktop_publish_event_threadsafe(
        SimpleNamespace(desktop_event_bus=_FailingEventBus()),
        "event.scheduling_failed",
        {},
    )

    assert (
        "[xinyu_core_bridge] desktop event publish scheduling failed: event.scheduling_failed: schedule failed"
        in capsys.readouterr().out
    )


def test_maybe_enqueue_tts_enqueues_owner_private_finished_reply(monkeypatch) -> None:
    monkeypatch.setattr(xinyu_bridge_desktop_event_tts.xinyu_qq_voice_reply, "voice_reply_enabled", lambda _kind: False)
    calls: list[tuple[str, dict[str, object]]] = []

    class _TTSOutput:
        def active(self) -> bool:
            return True

        def enqueue(self, reply: str, **kwargs) -> None:
            calls.append((reply, kwargs))

    xinyu_bridge_desktop_events.maybe_enqueue_tts(
        SimpleNamespace(tts_output=_TTSOutput()),
        {
            "message_type": "private",
            "source": "onebot",
            "adapter": "adapter-fallback",
            "metadata": {"is_owner_user": True, "source": "desktop"},
        },
        reply="hello",
        status="finished",
        reply_hash="",
        session_key="session-1",
        turn_id="turn-1",
    )

    assert calls == [
        (
            "hello",
            {
                "reply_hash": xinyu_bridge_desktop_events.visible_text_hash("hello"),
                "session_key": "session-1",
                "turn_id": "turn-1",
                "source": "desktop",
                "message_type": "private",
            },
        )
    ]


def test_maybe_enqueue_tts_skips_when_qq_voice_local_playback_takes_over(monkeypatch) -> None:
    monkeypatch.setattr(xinyu_bridge_desktop_event_tts.xinyu_qq_voice_reply, "voice_reply_enabled", lambda _kind: True)
    monkeypatch.setattr(xinyu_bridge_desktop_event_tts.xinyu_qq_voice_reply, "local_playback_enabled", lambda: True)
    calls: list[tuple[str, dict[str, object]]] = []

    class _TTSOutput:
        def active(self) -> bool:
            return True

        def enqueue(self, reply: str, **kwargs) -> None:
            calls.append((reply, kwargs))

    xinyu_bridge_desktop_events.maybe_enqueue_tts(
        SimpleNamespace(tts_output=_TTSOutput()),
        {"message_type": "private", "metadata": {"is_owner_user": True}},
        reply="hello",
        status="ok",
        reply_hash="hash",
        session_key="session-1",
        turn_id="turn-1",
    )

    assert calls == []


def test_maybe_enqueue_tts_skips_non_owner_inactive_bad_status_and_empty_reply(monkeypatch) -> None:
    monkeypatch.setattr(xinyu_bridge_desktop_event_tts.xinyu_qq_voice_reply, "voice_reply_enabled", lambda _kind: False)
    calls: list[tuple[str, dict[str, object]]] = []

    class _TTSOutput:
        def __init__(self, active: bool = True) -> None:
            self._active = active

        def active(self) -> bool:
            return self._active

        def enqueue(self, reply: str, **kwargs) -> None:
            calls.append((reply, kwargs))

    owner_payload = {"message_type": "private", "metadata": {"is_owner_user": True}}
    xinyu_bridge_desktop_events.maybe_enqueue_tts(
        SimpleNamespace(tts_output=_TTSOutput()),
        {"message_type": "private", "metadata": {"is_owner_user": False}},
        reply="hello",
        status="ok",
        reply_hash="hash",
        session_key="session-1",
        turn_id="turn-1",
    )
    xinyu_bridge_desktop_events.maybe_enqueue_tts(
        SimpleNamespace(tts_output=_TTSOutput(active=False)),
        owner_payload,
        reply="hello",
        status="ok",
        reply_hash="hash",
        session_key="session-1",
        turn_id="turn-1",
    )
    xinyu_bridge_desktop_events.maybe_enqueue_tts(
        SimpleNamespace(tts_output=_TTSOutput()),
        owner_payload,
        reply="hello",
        status="timeout",
        reply_hash="hash",
        session_key="session-1",
        turn_id="turn-1",
    )
    xinyu_bridge_desktop_events.maybe_enqueue_tts(
        SimpleNamespace(tts_output=_TTSOutput()),
        owner_payload,
        reply="",
        status="ok",
        reply_hash="hash",
        session_key="session-1",
        turn_id="turn-1",
    )
    xinyu_bridge_desktop_events.maybe_enqueue_tts(
        SimpleNamespace(tts_output=None),
        owner_payload,
        reply="hello",
        status="ok",
        reply_hash="hash",
        session_key="session-1",
        turn_id="turn-1",
    )

    assert calls == []


def test_maybe_enqueue_tts_logs_enqueue_warning(capsys, monkeypatch) -> None:
    monkeypatch.setattr(xinyu_bridge_desktop_event_tts.xinyu_qq_voice_reply, "voice_reply_enabled", lambda _kind: False)
    class _TTSOutput:
        def active(self) -> bool:
            return True

        def enqueue(self, reply: str, **kwargs) -> None:
            raise RuntimeError("tts failed")

    xinyu_bridge_desktop_events.maybe_enqueue_tts(
        SimpleNamespace(tts_output=_TTSOutput()),
        {"message_type": "private", "metadata": {"is_owner_user": True}},
        reply="hello",
        status="ok",
        reply_hash="hash",
        session_key="session-1",
        turn_id="turn-1",
    )

    assert "[xinyu_core_bridge] tts enqueue warning: tts failed" in capsys.readouterr().out


def test_desktop_publish_chat_started_builds_event_payload() -> None:
    calls: list[tuple[str, dict[str, object], dict[str, object]]] = []

    class _Runtime:
        def _desktop_turn_base(self, payload: dict[str, object], *, session_key: str, turn_id: str) -> dict[str, object]:
            return {"turnId": turn_id, "sessionHash": f"hash:{session_key}"}

        def _desktop_text_preview(self, text: str, *, limit: int) -> str:
            return f"{limit}:{text[:5]}"

        def _desktop_privacy_for_payload(self, payload: dict[str, object]) -> str:
            return "owner_private"

        async def _desktop_publish_event(
            self,
            event_type: str,
            payload: dict[str, object],
            **kwargs,
        ) -> dict[str, object]:
            calls.append((event_type, payload, kwargs))
            return {"id": "event-1"}

    asyncio.run(
        xinyu_bridge_desktop_events.desktop_publish_chat_started(
            _Runtime(),
            {"message_type": "private"},
            text="hello world",
            session_key="session-1",
            turn_id="turn-1",
            started_at="2026-06-05T01:00:00+08:00",
            active_sessions=3,
        )
    )

    assert calls == [
        (
            "chat.turn.started",
            {
                "turnId": "turn-1",
                "sessionHash": "hash:session-1",
                "startedAt": "2026-06-05T01:00:00+08:00",
                "textPreview": "180:hello",
                "textChars": 11,
                "activeSessions": 3,
            },
            {"privacy": "owner_private"},
        )
    ]


def test_desktop_publish_chat_finished_builds_event_payload_and_enqueues_tts() -> None:
    calls: list[tuple[str, object]] = []

    class _Runtime:
        def _desktop_turn_base(self, payload: dict[str, object], *, session_key: str, turn_id: str) -> dict[str, object]:
            return {"turnId": turn_id, "sessionHash": f"hash:{session_key}"}

        def _desktop_text_preview(self, text: str, *, limit: int) -> str:
            return f"{limit}:{text[:5]}"

        def _desktop_remember_turn(self, item: dict[str, object]) -> None:
            calls.append(("remember", dict(item)))

        def _desktop_privacy_for_payload(self, payload: dict[str, object]) -> str:
            return "owner_private"

        async def _desktop_publish_event(
            self,
            event_type: str,
            payload: dict[str, object],
            **kwargs,
        ) -> dict[str, object]:
            calls.append(("publish", (event_type, payload, kwargs)))
            return {"id": "event-1"}

        def _maybe_enqueue_tts(self, payload: dict[str, object], **kwargs) -> None:
            calls.append(("tts", kwargs))

    asyncio.run(
        xinyu_bridge_desktop_events.desktop_publish_chat_finished(
            _Runtime(),
            {"message_type": "private"},
            text="hello world",
            reply="reply text",
            session_key="session-1",
            turn_id="turn-1",
            started_at="2026-06-05T01:00:00+08:00",
            elapsed_ms=-5,
            status="timeout",
            notes=["note", "", *[f"extra-{index}" for index in range(20)]],
            memory_changed=True,
            archive_message_ids=list(range(10)),
            reply_hash="reply-hash",
            recall_event_id="recall-1",
            recall_count=-1,
            top_recall_sources=[f"source-{index}" for index in range(8)],
        )
    )

    item = calls[0][1]
    assert calls[0][0] == "remember"
    assert item["turnId"] == "turn-1"
    assert item["sessionHash"] == "hash:session-1"
    assert item["startedAt"] == "2026-06-05T01:00:00+08:00"
    assert item["status"] == "timeout"
    assert item["latencyMs"] == 0
    assert item["textPreview"] == "180:hello"
    assert item["replyPreview"] == "220:reply"
    assert item["textChars"] == 11
    assert item["replyChars"] == 10
    assert item["memoryChanged"] is True
    assert item["replyHash"] == "reply-hash"
    assert item["archiveMessageIds"] == [str(index) for index in range(8)]
    assert item["recallEventId"] == "recall-1"
    assert item["recallCount"] == 0
    assert item["topRecallSources"] == [f"source-{index}" for index in range(6)]
    assert item["notes"] == ["note", *[f"extra-{index}" for index in range(11)]]
    assert calls[1] == (
        "publish",
        ("chat.turn.finished", item, {"privacy": "owner_private", "severity": "warn"}),
    )
    assert calls[2] == (
        "tts",
        {
            "reply": "reply text",
            "status": "timeout",
            "reply_hash": "reply-hash",
            "session_key": "session-1",
            "turn_id": "turn-1",
        },
    )


def test_desktop_publish_memory_recall_skips_disabled_or_unneeded_retrieval() -> None:
    class _Runtime:
        async def _desktop_publish_event(self, *args, **kwargs) -> dict[str, object]:
            raise AssertionError("disabled memory recall should not publish")

    assert asyncio.run(
        xinyu_bridge_desktop_events.desktop_publish_memory_recall(
            _Runtime(),
            {},
            SimpleNamespace(notes=["retrieval_disabled"]),
            session_key="session-1",
            turn_id="turn-1",
        )
    ) == {}
    assert asyncio.run(
        xinyu_bridge_desktop_events.desktop_publish_memory_recall(
            _Runtime(),
            {},
            SimpleNamespace(notes=["retrieval_not_needed"]),
            session_key="session-1",
            turn_id="turn-1",
        )
    ) == {}


def test_desktop_publish_memory_recall_builds_event_payload_and_remembers_event() -> None:
    calls: list[tuple[str, dict[str, object], dict[str, object]]] = []
    remembered: list[dict[str, object]] = []

    class _Runtime:
        def _desktop_recall_item(self, item: dict[str, object]) -> dict[str, object]:
            return {"memoryId": item["id"], "source": item["source"]}

        def _desktop_memory_route_payload(self, route_plan: object) -> dict[str, object]:
            assert route_plan == "route-plan"
            return {
                "selectedExperts": ["profile", "preferences"],
                "currentTurnFacts": ["likes tea"],
                "routeScore": 0.75,
            }

        def _desktop_turn_base(self, payload: dict[str, object], *, session_key: str, turn_id: str) -> dict[str, object]:
            return {"turnId": turn_id, "sessionHash": f"hash:{session_key}"}

        def _desktop_hash(self, value: object) -> str:
            return f"hash:{value}"

        def _desktop_privacy_for_payload(self, payload: dict[str, object]) -> str:
            return "owner_private"

        async def _desktop_publish_event(
            self,
            event_type: str,
            payload: dict[str, object],
            **kwargs,
        ) -> dict[str, object]:
            calls.append((event_type, payload, kwargs))
            return {"id": "event-1", "ts": "2026-06-05T01:00:00+08:00"}

        def _desktop_remember_memory_event(self, item: dict[str, object]) -> None:
            remembered.append(dict(item))

    raw_items = [
        {"id": index, "source": source}
        for index, source in enumerate(["alpha", "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"])
    ]
    result = SimpleNamespace(
        notes=[f"note-{index}" for index in range(10)],
        items=raw_items,
        query_text="hello memory",
        route_plan="route-plan",
        turn_id="recall-turn-1",
    )

    event = asyncio.run(
        xinyu_bridge_desktop_events.desktop_publish_memory_recall(
            _Runtime(),
            {"message_type": "private"},
            result,
            session_key="session-1",
            turn_id="turn-1",
        )
    )

    items = [{"memoryId": index, "source": source} for index, source in enumerate(
        ["alpha", "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta"]
    )]
    event_payload = {
        "turnId": "turn-1",
        "sessionHash": "hash:session-1",
        "status": "used",
        "recallTurnId": "recall-turn-1",
        "queryHash": "hash:hello memory",
        "queryChars": 12,
        "itemCount": 9,
        "topSources": ["alpha", "beta", "gamma", "delta", "epsilon", "zeta"],
        "selectedExperts": ["profile", "preferences"],
        "currentTurnFacts": ["likes tea"],
        "route": {
            "selectedExperts": ["profile", "preferences"],
            "currentTurnFacts": ["likes tea"],
            "routeScore": 0.75,
        },
        "items": items,
        "notes": [f"note-{index}" for index in range(8)],
    }

    assert event == {"id": "event-1", "ts": "2026-06-05T01:00:00+08:00"}
    assert calls == [
        (
            "memory.recall.used",
            event_payload,
            {"privacy": "owner_private"},
        )
    ]
    assert remembered == [
        {
            "eventId": "event-1",
            "ts": "2026-06-05T01:00:00+08:00",
            **event_payload,
        }
    ]


def test_desktop_publish_memory_recall_does_not_remember_empty_publish_result() -> None:
    calls: list[tuple[str, dict[str, object], dict[str, object]]] = []
    remembered: list[dict[str, object]] = []

    class _Runtime:
        def _desktop_recall_item(self, item: dict[str, object]) -> dict[str, object]:
            raise AssertionError("empty recall should not project items")

        def _desktop_memory_route_payload(self, route_plan: object) -> dict[str, object]:
            return {"selectedExperts": [], "currentTurnFacts": []}

        def _desktop_turn_base(self, payload: dict[str, object], *, session_key: str, turn_id: str) -> dict[str, object]:
            return {"turnId": turn_id}

        def _desktop_hash(self, value: object) -> str:
            return f"hash:{value}"

        def _desktop_privacy_for_payload(self, payload: dict[str, object]) -> str:
            return "internal_summary"

        async def _desktop_publish_event(
            self,
            event_type: str,
            payload: dict[str, object],
            **kwargs,
        ) -> dict[str, object]:
            calls.append((event_type, payload, kwargs))
            return {}

        def _desktop_remember_memory_event(self, item: dict[str, object]) -> None:
            remembered.append(dict(item))

    event = asyncio.run(
        xinyu_bridge_desktop_events.desktop_publish_memory_recall(
            _Runtime(),
            {},
            SimpleNamespace(notes=[], items=[], query_text="", route_plan=None, turn_id=""),
            session_key="session-1",
            turn_id="turn-1",
        )
    )

    assert event == {}
    assert calls == [
        (
            "memory.recall.used",
            {
                "turnId": "turn-1",
                "status": "empty",
                "recallTurnId": "",
                "queryHash": "hash:",
                "queryChars": 0,
                "itemCount": 0,
                "topSources": [],
                "selectedExperts": [],
                "currentTurnFacts": [],
                "route": {"selectedExperts": [], "currentTurnFacts": []},
                "items": [],
                "notes": [],
            },
            {"privacy": "internal_summary"},
        )
    ]
    assert remembered == []
