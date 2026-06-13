from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import xinyu_bridge_desktop_proactive_routes as desktop_proactive_routes
from xinyu_bridge_desktop_recent_routes import (
    desktop_chat_recent,
    desktop_memory_recent,
    desktop_remember_memory_event,
    desktop_remember_turn,
)
from xinyu_bridge_desktop_surface_state_store import (
    DESKTOP_SURFACE_STATE_STORE_RUNTIME_ATTR,
    LocalDesktopSurfaceStateStore,
    desktop_surface_state_store_readiness,
)
from xinyu_proactive_context_adapter import runtime_owner_private_turns
from xinyu_serviceization_contracts import service_contract_by_id


def test_desktop_surface_state_store_contract_matches_service_manifest() -> None:
    manifest = service_contract_by_id("desktop_surface")

    assert "xinyu_bridge_desktop_surface_state_store.py" in manifest.contract_modules
    assert "tests/test_desktop_surface_state_store.py" in manifest.validation_tests
    assert manifest.process_split_ready is True
    assert "Ready for a controlled desktop_surface split" in manifest.process_split_gate


def test_desktop_recent_routes_use_runtime_state_store_attr(tmp_path: Path) -> None:
    store = LocalDesktopSurfaceStateStore(
        recent_turns=[{"id": "store-turn"}],
        recent_memory_events=[{"id": "store-memory"}],
    )
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _desktop_recent_turns=[{"id": "legacy-turn"}],
        _desktop_recent_memory_events=[{"id": "legacy-memory"}],
        **{DESKTOP_SURFACE_STATE_STORE_RUNTIME_ATTR: store},
    )

    chat = asyncio.run(desktop_chat_recent(runtime, {"limit": 1}))
    memory = asyncio.run(desktop_memory_recent(runtime, {"limit": 1}))

    assert chat["items"] == [{"id": "store-turn"}]
    assert chat["notes"] == ["desktop_chat_recent_v0_runtime_buffer"]
    assert memory["items"] == [{"id": "store-memory"}]
    assert memory["notes"] == ["desktop_memory_recent_v0_runtime_buffer"]


def test_desktop_recent_store_fallback_preserves_legacy_runtime_lists(tmp_path: Path) -> None:
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _desktop_recent_turns=[{"id": "turn-1"}, {"id": "turn-2"}],
        _desktop_recent_memory_events=[{"id": "memory-1"}, {"id": "memory-2"}],
    )

    chat = asyncio.run(desktop_chat_recent(runtime, {"limit": 1}))
    memory = asyncio.run(desktop_memory_recent(runtime, {"limit": 1}))

    assert chat["items"] == [{"id": "turn-2"}]
    assert memory["items"] == [{"id": "memory-2"}]


def test_desktop_recent_writers_copy_and_trim_store_items(tmp_path: Path, monkeypatch) -> None:
    import xinyu_bridge_desktop_recent_routes

    monkeypatch.setattr(xinyu_bridge_desktop_recent_routes, "DESKTOP_RECENT_TURNS_MAX", 2)
    monkeypatch.setattr(xinyu_bridge_desktop_recent_routes, "DESKTOP_RECENT_MEMORY_EVENTS_MAX", 2)
    store = LocalDesktopSurfaceStateStore(
        recent_turns=[{"id": "turn-1"}, {"id": "turn-2"}],
        recent_memory_events=[{"id": "memory-1"}, {"id": "memory-2"}],
    )
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        **{DESKTOP_SURFACE_STATE_STORE_RUNTIME_ATTR: store},
    )
    turn = {"id": "turn-3"}
    memory = {"id": "memory-3"}

    desktop_remember_turn(runtime, turn)
    desktop_remember_memory_event(runtime, memory)
    turn["id"] = "mutated-turn"
    memory["id"] = "mutated-memory"

    assert store.recent_turns() == [{"id": "turn-2"}, {"id": "turn-3"}]
    assert store.recent_memory_events() == [{"id": "memory-2"}, {"id": "memory-3"}]


def test_runtime_owner_private_turns_uses_state_store(tmp_path: Path) -> None:
    store = LocalDesktopSurfaceStateStore(
        recent_turns=[
            {"id": "legacy", "privacy": "group"},
            {"id": "owner", "privacy": "owner_private", "text": "hi"},
        ],
    )
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _desktop_recent_turns=[],
        **{DESKTOP_SURFACE_STATE_STORE_RUNTIME_ATTR: store},
    )

    assert runtime_owner_private_turns(runtime) == [
        {"id": "owner", "privacy": "owner_private", "text": "hi"}
    ]


def test_desktop_proactive_primitives_use_runtime_state_store_attr(tmp_path: Path) -> None:
    store = LocalDesktopSurfaceStateStore(
        proactive_inbox={
            "candidate-1": {"candidateId": "candidate-1", "status": "ready", "source": "state"}
        }
    )
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _desktop_proactive_inbox={},
        _desktop_proactive_expired=lambda expires_at: expires_at == "past",
        **{DESKTOP_SURFACE_STATE_STORE_RUNTIME_ATTR: store},
    )

    desktop_proactive_routes.desktop_upsert_proactive_inbox(
        runtime,
        {"candidateId": "candidate-1", "deliveryLevel": "preview_only"},
    )
    existing = desktop_proactive_routes.desktop_proactive_existing(runtime, "candidate-1")
    existing["status"] = "mutated-copy"

    assert store.proactive_existing("candidate-1") == {
        "candidateId": "candidate-1",
        "status": "ready",
        "source": "state",
        "deliveryLevel": "preview_only",
    }
    assert runtime._desktop_proactive_inbox == {}

    desktop_proactive_routes.desktop_upsert_proactive_inbox(
        runtime,
        {"candidateId": "initiative", "status": "ready", "source": "initiative_orchestrator"},
    )
    desktop_proactive_routes.desktop_remove_proactive_state_items(runtime)
    assert set(store.proactive_inbox_items()) == {"initiative"}

    desktop_proactive_routes.desktop_upsert_proactive_inbox(
        runtime,
        {"candidateId": "expired", "status": "ready", "expiresAt": "past"},
    )
    desktop_proactive_routes.desktop_prune_proactive_inbox(runtime)
    assert set(store.proactive_inbox_items()) == {"initiative"}

    desktop_proactive_routes.desktop_clear_proactive_inbox(runtime)
    assert store.proactive_inbox_items() == {}


def test_desktop_proactive_history_uses_runtime_state_store_attr(tmp_path: Path) -> None:
    store = LocalDesktopSurfaceStateStore()
    traces: list[str] = []
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _desktop_proactive_history=[],
        _trace_autonomous=traces.append,
        **{DESKTOP_SURFACE_STATE_STORE_RUNTIME_ATTR: store},
    )

    desktop_proactive_routes.desktop_remember_proactive_history(
        runtime,
        {
            "candidateId": "candidate-1",
            "status": "answered",
            "updatedAt": "2026-06-05T01:00:00+08:00",
        },
    )

    path = tmp_path / desktop_proactive_routes.DESKTOP_PROACTIVE_HISTORY_REL
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows == store.proactive_history_items()
    assert runtime._desktop_proactive_history == []
    assert traces == []

    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n"
        + json.dumps(
            {
                "candidateId": "candidate-2",
                "status": "dismissed",
                "updatedAt": "2026-06-05T01:01:00+08:00",
            }
        ),
        encoding="utf-8",
    )
    desktop_proactive_routes.desktop_load_proactive_history(runtime)

    assert [item["candidateId"] for item in store.proactive_history_items()] == [
        "candidate-1",
        "candidate-2",
    ]
    assert runtime._desktop_proactive_history == []


def test_desktop_surface_state_store_readiness_reports_runtime_store_mode(tmp_path: Path) -> None:
    store = LocalDesktopSurfaceStateStore()
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        **{DESKTOP_SURFACE_STATE_STORE_RUNTIME_ATTR: store},
    )

    readiness = desktop_surface_state_store_readiness(runtime)

    assert readiness.service_id == "desktop_surface"
    assert readiness.mode == "desktop_surface_state_store_local_in_memory"
    assert readiness.ready is True
    assert "recent_and_proactive_buffers_use_state_store" in readiness.notes
