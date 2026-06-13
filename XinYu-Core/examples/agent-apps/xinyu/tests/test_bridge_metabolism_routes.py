from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import xinyu_bridge_metabolism_routes


def test_select_desktop_metabolism_ticket_prefers_running_then_newer() -> None:
    tickets = [
        {"ticket_id": "requested-new", "status": "requested", "created_at": "2026-06-05T10:00:00"},
        {"ticket_id": "approved-old", "status": "approved", "created_at": "2026-06-05T09:00:00"},
        {"ticket_id": "running-old", "status": "running", "created_at": "2026-06-05T08:00:00"},
    ]

    assert xinyu_bridge_metabolism_routes.select_desktop_metabolism_ticket(tickets)["ticket_id"] == "running-old"


def test_select_desktop_metabolism_ticket_breaks_ties_by_created_and_id() -> None:
    tickets = [
        {"ticket_id": "requested-a", "status": "requested", "created_at": "2026-06-05T10:00:00"},
        {"ticket_id": "requested-b", "status": "requested", "created_at": "2026-06-05T10:00:00"},
    ]

    assert xinyu_bridge_metabolism_routes.select_desktop_metabolism_ticket(tickets)["ticket_id"] == "requested-b"
    assert xinyu_bridge_metabolism_routes.select_desktop_metabolism_ticket([]) == {}


def test_desktop_open_metabolism_ticket_uses_runtime_root(tmp_path, monkeypatch) -> None:
    calls: list[tuple[object, object]] = []

    def fake_list(root, *, statuses):
        calls.append((root, statuses))
        return [{"ticket_id": "ticket-1", "status": "requested", "created_at": "2026-06-05T10:00:00"}]

    monkeypatch.setattr(xinyu_bridge_metabolism_routes, "list_metabolism_tickets", fake_list)

    assert (
        xinyu_bridge_metabolism_routes.desktop_open_metabolism_ticket(SimpleNamespace(xinyu_dir=tmp_path))[
            "ticket_id"
        ]
        == "ticket-1"
    )
    assert calls == [(tmp_path, {"requested", "approved", "running"})]


def test_metabolism_input_window_counts_recent_context_and_self_choice() -> None:
    window = xinyu_bridge_metabolism_routes.metabolism_input_window(
        proactive_items=[{"candidateId": "p1"}, "ignored"],
        recent_turns=[{"turnId": "t1"}, {"turnId": "t2"}, "ignored"],
        recent_memory_events=[
            {"summary": "suppressed local residue"},
            {"summary": "normal memory"},
            "suppressed string marker",
        ],
        self_choice_dream_bias={"dream": "bias"},
    )

    assert window == {
        "suppressed_residue_count": 2,
        "memory_event_count": 2,
        "proactive_item_count": 1,
        "recent_turn_count": 2,
        "self_choice": {"dream": "bias"},
    }


def test_publish_metabolism_runner_result_skips_empty_settled_items() -> None:
    class _Runtime:
        async def _desktop_publish_event(self, *args, **kwargs) -> None:
            raise AssertionError("empty settled result should not publish")

    asyncio.run(
        xinyu_bridge_metabolism_routes.publish_metabolism_runner_result(
            _Runtime(),
            {"settled": []},
            trigger="tick",
        )
    )
    asyncio.run(
        xinyu_bridge_metabolism_routes.publish_metabolism_runner_result(
            _Runtime(),
            {},
            trigger="tick",
        )
    )


def test_publish_metabolism_runner_result_publishes_settled_and_failed_items() -> None:
    calls: list[tuple[str, dict[str, object], dict[str, object]]] = []

    class _SelfChoiceStore:
        def __init__(self) -> None:
            self.events: list[str] = []
            self.consume_count = 0

        async def apply_event_impulse(self, event: str) -> dict[str, object]:
            self.events.append(event)
            return {"applied": event}

        async def consume_hibernation_residue_for_metabolism(self) -> None:
            self.consume_count += 1

    class _Runtime:
        def __init__(self) -> None:
            self.self_choice_store = _SelfChoiceStore()

        async def _desktop_publish_event(
            self,
            event_type: str,
            payload: dict[str, object],
            **kwargs,
        ) -> None:
            calls.append((event_type, payload, kwargs))

    runtime = _Runtime()

    asyncio.run(
        xinyu_bridge_metabolism_routes.publish_metabolism_runner_result(
            runtime,
            {
                "settled": [
                    {
                        "ticket": {"ticket_id": "ticket-1", "status": "settled"},
                        "metabolism_path": "metabolism/a.json",
                        "dream_path": "dream/a.json",
                        "notes": ["settled"],
                    },
                    "ignored",
                    {
                        "ticket": {"ticket_id": "ticket-2", "status": "failed"},
                        "metabolism_path": "metabolism/b.json",
                        "dream_path": "dream/b.json",
                        "notes": ["failed"],
                    },
                    {
                        "ticket": {"ticket_id": "ticket-3", "status": "running"},
                        "notes": ["running"],
                    },
                ]
            },
            trigger="wakeup",
        )
    )

    assert runtime.self_choice_store.events == ["ticket_settled", "ticket_failed"]
    assert runtime.self_choice_store.consume_count == 2
    assert calls == [
        (
            "metabolism_ticket_updated",
            {
                "trigger": "wakeup",
                "ticket": {"ticket_id": "ticket-1", "status": "settled"},
                "metabolism_path": "metabolism/a.json",
                "dream_path": "dream/a.json",
                "selfChoiceState": {"applied": "ticket_settled"},
                "notes": ["settled"],
            },
            {"severity": "info"},
        ),
        (
            "metabolism_ticket_updated",
            {
                "trigger": "wakeup",
                "ticket": {"ticket_id": "ticket-2", "status": "failed"},
                "metabolism_path": "metabolism/b.json",
                "dream_path": "dream/b.json",
                "selfChoiceState": {"applied": "ticket_failed"},
                "notes": ["failed"],
            },
            {"severity": "info"},
        ),
        (
            "metabolism_ticket_updated",
            {
                "trigger": "wakeup",
                "ticket": {"ticket_id": "ticket-3", "status": "running"},
                "metabolism_path": "",
                "dream_path": "",
                "selfChoiceState": {},
                "notes": ["running"],
            },
            {"severity": "info"},
        ),
    ]


def test_run_due_metabolism_once_runs_tickets_and_updates_runtime(tmp_path, monkeypatch) -> None:
    run_calls: list[tuple[object, str, int]] = []
    publish_calls: list[tuple[dict[str, object], str]] = []

    def fake_run_due(root, *, runner_id: str, max_tickets: int) -> dict[str, object]:
        run_calls.append((root, runner_id, max_tickets))
        return {"ran": 2, "settled": []}

    async def fake_publish(result: dict[str, object], *, trigger: str) -> None:
        publish_calls.append((result, trigger))

    monkeypatch.setattr(xinyu_bridge_metabolism_routes, "run_due_metabolism_tickets", fake_run_due)
    monkeypatch.setattr(xinyu_bridge_metabolism_routes.os, "getpid", lambda: 4321)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _closed=False,
        _metabolism_in_progress=False,
        _metabolism_run_count=3,
        _metabolism_last_result={},
        _metabolism_last_started_at="",
        _metabolism_last_success_at="",
        _metabolism_last_error="old",
        _publish_metabolism_runner_result=fake_publish,
    )

    result = asyncio.run(xinyu_bridge_metabolism_routes.run_due_metabolism_once(runtime, trigger="wakeup"))

    assert result == {"ran": 2, "settled": []}
    assert run_calls == [(tmp_path, "core_bridge:4321:wakeup", 3)]
    assert runtime._metabolism_run_count == 5
    assert runtime._metabolism_last_result == result
    assert runtime._metabolism_last_started_at
    assert runtime._metabolism_last_success_at
    assert runtime._metabolism_last_error == ""
    assert runtime._metabolism_in_progress is False
    assert publish_calls == [(result, "wakeup")]


def test_run_due_metabolism_once_skips_closed_or_in_progress() -> None:
    closed = SimpleNamespace(_closed=True, _metabolism_in_progress=False)
    busy = SimpleNamespace(_closed=False, _metabolism_in_progress=True)

    assert asyncio.run(xinyu_bridge_metabolism_routes.run_due_metabolism_once(closed, trigger="tick")) == {
        "ran": 0,
        "notes": ["closed_or_in_progress"],
    }
    assert asyncio.run(xinyu_bridge_metabolism_routes.run_due_metabolism_once(busy, trigger="tick")) == {
        "ran": 0,
        "notes": ["closed_or_in_progress"],
    }


def test_run_due_metabolism_once_records_failure_event(tmp_path, monkeypatch) -> None:
    publish_calls: list[tuple[str, dict[str, object], dict[str, object]]] = []

    class _SelfChoiceStore:
        def __init__(self) -> None:
            self.events: list[str] = []

        async def apply_event_impulse(self, event: str) -> dict[str, object]:
            self.events.append(event)
            return {"event": event}

    def fake_run_due(*args, **kwargs):
        raise RuntimeError("boom")

    async def fake_publish_event(event_type: str, payload: dict[str, object], **kwargs) -> None:
        publish_calls.append((event_type, payload, kwargs))

    monkeypatch.setattr(xinyu_bridge_metabolism_routes, "run_due_metabolism_tickets", fake_run_due)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _closed=False,
        _metabolism_in_progress=False,
        _metabolism_run_count=0,
        _metabolism_last_result={},
        _metabolism_last_started_at="",
        _metabolism_last_success_at="",
        _metabolism_last_error="",
        self_choice_store=_SelfChoiceStore(),
        _desktop_publish_event=fake_publish_event,
    )

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(xinyu_bridge_metabolism_routes.run_due_metabolism_once(runtime, trigger="tick"))

    assert runtime._metabolism_in_progress is False
    assert runtime._metabolism_last_error == "RuntimeError: boom"
    assert runtime.self_choice_store.events == ["ticket_failed"]
    assert publish_calls == [
        (
            "metabolism_runner_failed",
            {
                "error": "RuntimeError: boom",
                "trigger": "tick",
                "selfChoiceState": {"event": "ticket_failed"},
            },
            {"severity": "error"},
        )
    ]


def test_metabolism_runner_loop_runs_tick_then_wakeup() -> None:
    calls: list[str] = []

    class _Wakeup:
        async def wait(self) -> None:
            calls.append("wait")

        def clear(self) -> None:
            calls.append("clear")

    async def run_due(*, trigger: str) -> dict[str, object]:
        calls.append(trigger)
        if trigger == "wakeup":
            runtime._closed = True
        return {"ran": 0}

    runtime = SimpleNamespace(
        _closed=False,
        _metabolism_wakeup_event=_Wakeup(),
        _metabolism_last_error="",
        metabolism_runner_interval_seconds=30,
        _run_due_metabolism_once=run_due,
    )

    asyncio.run(xinyu_bridge_metabolism_routes.metabolism_runner_loop(runtime))

    assert calls == ["tick", "wait", "clear", "wakeup"]
    assert runtime._metabolism_last_error == ""


def test_metabolism_runner_loop_records_tick_error_and_exits_after_wakeup() -> None:
    calls: list[str] = []

    class _Wakeup:
        async def wait(self) -> None:
            calls.append("wait")
            runtime._closed = True

        def clear(self) -> None:
            calls.append("clear")

    async def run_due(*, trigger: str) -> dict[str, object]:
        calls.append(trigger)
        raise RuntimeError("boom")

    runtime = SimpleNamespace(
        _closed=False,
        _metabolism_wakeup_event=_Wakeup(),
        _metabolism_last_error="",
        metabolism_runner_interval_seconds=30,
        _run_due_metabolism_once=run_due,
    )

    asyncio.run(xinyu_bridge_metabolism_routes.metabolism_runner_loop(runtime))

    assert calls == ["tick", "wait", "clear"]
    assert runtime._metabolism_last_error == "tick_error:RuntimeError('boom')"


def test_wake_metabolism_runner_sets_runtime_event_when_present() -> None:
    class _Wakeup:
        def __init__(self) -> None:
            self.set_called = False

        def set(self) -> None:
            self.set_called = True

    wakeup = _Wakeup()

    xinyu_bridge_metabolism_routes.wake_metabolism_runner(SimpleNamespace(_metabolism_wakeup_event=wakeup))
    xinyu_bridge_metabolism_routes.wake_metabolism_runner(SimpleNamespace(_metabolism_wakeup_event=None))

    assert wakeup.set_called is True
