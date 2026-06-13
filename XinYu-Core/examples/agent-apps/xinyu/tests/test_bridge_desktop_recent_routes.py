from __future__ import annotations

import asyncio
from pathlib import Path

import xinyu_bridge_desktop_recent_routes


class _EventBus:
    def __init__(self) -> None:
        self.requested_limit: int | None = None

    async def recent(self, limit: int) -> list[dict[str, object]]:
        self.requested_limit = limit
        return [{"id": "evt-1", "type": "window"}]

    async def latest_event_id(self) -> str:
        return "evt-1"


class _Runtime:
    def __init__(self, xinyu_dir: Path) -> None:
        self.xinyu_dir = xinyu_dir
        self.desktop_event_bus = _EventBus()
        self._desktop_recent_turns = [{"id": "turn-1"}, {"id": "turn-2"}]
        self._desktop_recent_memory_events = [{"id": "mem-1"}, {"id": "mem-2"}]


def test_desktop_events_recent_delegates_to_event_bus(tmp_path: Path) -> None:
    runtime = _Runtime(tmp_path)

    result = asyncio.run(
        xinyu_bridge_desktop_recent_routes.desktop_events_recent(runtime, {"limit": "2"})
    )

    assert runtime.desktop_event_bus.requested_limit == 2
    assert result == {
        "version": 1,
        "items": [{"id": "evt-1", "type": "window"}],
        "latestEventId": "evt-1",
        "notes": ["desktop_events_recent_v0"],
    }


def test_desktop_recent_buffers_return_limited_items_with_runtime_notes(tmp_path: Path) -> None:
    runtime = _Runtime(tmp_path)

    chat = asyncio.run(xinyu_bridge_desktop_recent_routes.desktop_chat_recent(runtime, {"limit": 1}))
    memory = asyncio.run(xinyu_bridge_desktop_recent_routes.desktop_memory_recent(runtime, {"limit": 1}))

    assert chat == {
        "version": 1,
        "items": [{"id": "turn-2"}],
        "notes": ["desktop_chat_recent_v0_runtime_buffer"],
    }
    assert memory == {
        "version": 1,
        "items": [{"id": "mem-2"}],
        "notes": ["desktop_memory_recent_v0_runtime_buffer"],
    }


def test_desktop_recent_buffer_writers_copy_and_trim_items(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(xinyu_bridge_desktop_recent_routes, "DESKTOP_RECENT_TURNS_MAX", 2)
    monkeypatch.setattr(xinyu_bridge_desktop_recent_routes, "DESKTOP_RECENT_MEMORY_EVENTS_MAX", 2)
    runtime = _Runtime(tmp_path)
    turn = {"id": "turn-3"}
    memory = {"id": "mem-3"}

    xinyu_bridge_desktop_recent_routes.desktop_remember_turn(runtime, turn)
    xinyu_bridge_desktop_recent_routes.desktop_remember_memory_event(runtime, memory)
    turn["id"] = "mutated-turn"
    memory["id"] = "mutated-memory"

    assert runtime._desktop_recent_turns == [{"id": "turn-2"}, {"id": "turn-3"}]
    assert runtime._desktop_recent_memory_events == [{"id": "mem-2"}, {"id": "mem-3"}]


def test_desktop_memory_growth_candidates_clamps_limit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[Path, int]] = []

    def _fake_list_growth_candidate_promotions(xinyu_dir: Path, *, limit: int) -> dict[str, object]:
        calls.append((xinyu_dir, limit))
        return {"ok": True, "items": [{"id": "candidate-1"}]}

    monkeypatch.setattr(
        xinyu_bridge_desktop_recent_routes,
        "list_growth_candidate_promotions",
        _fake_list_growth_candidate_promotions,
    )
    runtime = _Runtime(tmp_path)

    result = asyncio.run(
        xinyu_bridge_desktop_recent_routes.desktop_memory_growth_candidates(runtime, {"limit": 1000})
    )

    assert calls == [(tmp_path, 200)]
    assert result == {"ok": True, "items": [{"id": "candidate-1"}]}
