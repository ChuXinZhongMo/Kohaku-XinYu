from __future__ import annotations

import asyncio
from types import SimpleNamespace

from xinyu_bridge_desktop_snapshot_context import collect_desktop_snapshot_context
from xinyu_bridge_desktop_surface_projection_backend import (
    DESKTOP_SURFACE_PROJECTION_BACKEND_RUNTIME_ATTR,
    DesktopSurfaceProjectionSnapshot,
    collect_desktop_surface_projection,
    desktop_surface_projection_backend_readiness,
)
from xinyu_serviceization_contracts import service_contract_by_id


class StubProjectionBackend:
    mode = "stub_projection_backend"

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def collect(self, runtime: object, payload: dict[str, object]) -> DesktopSurfaceProjectionSnapshot:
        self.calls.append(dict(payload))
        return DesktopSurfaceProjectionSnapshot(
            proactive_items=[{"candidateId": "candidate-1"}],
            proactive_history=[{"candidateId": "history-1"}],
            recent_turns=[{"turnId": "turn-1"}],
            recent_memory_events=[{"eventId": "memory-1"}],
        )


def test_desktop_surface_projection_backend_contract_matches_service_manifest() -> None:
    manifest = service_contract_by_id("desktop_surface")

    assert "xinyu_bridge_desktop_surface_projection_backend.py" in manifest.contract_modules
    assert "tests/test_desktop_surface_projection_backend.py" in manifest.validation_tests
    assert manifest.process_split_ready is True
    assert "Ready for a controlled desktop_surface split" in manifest.process_split_gate


def test_default_projection_backend_uses_current_in_process_facades() -> None:
    calls: list[str] = []

    async def proactive_inbox(payload: dict[str, object]) -> dict[str, object]:
        calls.append("proactive")
        return {"items": [{"candidateId": "candidate-1"}], "history": [{"candidateId": "history-1"}]}

    async def chat_recent(payload: dict[str, object]) -> dict[str, object]:
        calls.append("chat")
        return {"items": [{"turnId": "turn-1"}]}

    async def memory_recent(payload: dict[str, object]) -> dict[str, object]:
        calls.append("memory")
        return {"items": [{"eventId": "memory-1"}]}

    runtime = SimpleNamespace(
        desktop_proactive_inbox=proactive_inbox,
        desktop_chat_recent=chat_recent,
        desktop_memory_recent=memory_recent,
    )

    projection = asyncio.run(collect_desktop_surface_projection(runtime, {"limit": 2}))

    assert calls == ["proactive", "chat", "memory"]
    assert projection.proactive_items == [{"candidateId": "candidate-1"}]
    assert projection.proactive_history == [{"candidateId": "history-1"}]
    assert projection.recent_turns == [{"turnId": "turn-1"}]
    assert projection.recent_memory_events == [{"eventId": "memory-1"}]


def test_runtime_projection_backend_attr_replaces_snapshot_projection_calls() -> None:
    backend = StubProjectionBackend()

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("snapshot context should use projection backend")

    entropy = SimpleNamespace(model_dump=lambda mode: {"entropy_level": 0.1, "mode": mode})
    runtime = SimpleNamespace(
        **{DESKTOP_SURFACE_PROJECTION_BACKEND_RUNTIME_ATTR: backend},
        _ensure_self_choice_ready=lambda: _async_none(),
        self_choice_store=SimpleNamespace(
            apply_time_decay=lambda: _async_none(),
            snapshot_private=lambda: _async_value({"private": True}),
            snapshot_public=lambda: _async_value({"public": True}),
        ),
        _desktop_event_state=lambda: _async_value({"latest_event_id": "event-1"}),
        desktop_proactive_inbox=forbidden,
        desktop_chat_recent=forbidden,
        desktop_memory_recent=forbidden,
        _desktop_active_desires=lambda **kwargs: _async_value(
            [{"inputs": {key: kwargs[key] for key in ("proactive_items", "recent_turns", "recent_memory_events")}}]
        ),
        xinyu_dir="xinyu",
        health_snapshot=lambda: {"runtime_presence": {"initiative_metrics": {"observed": True}}},
    )

    context = asyncio.run(
        collect_desktop_snapshot_context(
            runtime,
            {"limit": 3},
            sample_environment_func=lambda root: {"root": root},
            build_entropy_state_func=lambda **kwargs: entropy,
            read_action_digest_func=lambda root, limit: {"root": root, "limit": limit},
        )
    )

    assert backend.calls == [{"limit": 3}]
    assert context.proactive_items == [{"candidateId": "candidate-1"}]
    assert context.proactive_history == [{"candidateId": "history-1"}]
    assert context.recent_turns == [{"turnId": "turn-1"}]
    assert context.recent_memory_events == [{"eventId": "memory-1"}]
    assert context.active_desires == [
        {
            "inputs": {
                "proactive_items": [{"candidateId": "candidate-1"}],
                "recent_turns": [{"turnId": "turn-1"}],
                "recent_memory_events": [{"eventId": "memory-1"}],
            }
        }
    ]
    assert context.self_choice_public == {"public": True}
    assert context.action_digest == {"root": "xinyu", "limit": 5}
    assert context.initiative_metrics == {"observed": True}


def test_projection_backend_readiness_reports_runtime_backend_mode() -> None:
    backend = StubProjectionBackend()
    runtime = SimpleNamespace(**{DESKTOP_SURFACE_PROJECTION_BACKEND_RUNTIME_ATTR: backend})

    readiness = desktop_surface_projection_backend_readiness(runtime)

    assert readiness.service_id == "desktop_surface"
    assert readiness.mode == "stub_projection_backend"
    assert readiness.ready is True
    assert "projection_backend_contract_ready" in readiness.notes


async def _async_none() -> None:
    return None


async def _async_value(value: object) -> object:
    return value
