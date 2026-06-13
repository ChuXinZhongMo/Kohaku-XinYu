from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import xinyu_bridge_desktop_snapshot_service
import xinyu_bridge_desktop_recent_routes
from xinyu_bridge_desktop_snapshot_context import DesktopSnapshotContext, collect_desktop_snapshot_context
from xinyu_bridge_desktop_recent_routes import desktop_memory_growth_candidates
from xinyu_bridge_desktop_surface_projection_backend import (
    DESKTOP_SURFACE_PROJECTION_BACKEND_RUNTIME_ATTR,
    DesktopSurfaceProjectionSnapshot,
)
from xinyu_bridge_desktop_surface_snapshot_state_backend import (
    DESKTOP_SURFACE_SNAPSHOT_STATE_BACKEND_RUNTIME_ATTR,
    desktop_surface_snapshot_state_backend_readiness,
)
from xinyu_serviceization_contracts import service_contract_by_id


class StubProjectionBackend:
    mode = "stub_projection_backend"

    async def collect(self, runtime: object, payload: dict[str, object]) -> DesktopSurfaceProjectionSnapshot:
        return DesktopSurfaceProjectionSnapshot(
            proactive_items=[{"candidateId": "candidate-1"}],
            proactive_history=[{"candidateId": "history-1"}],
            recent_turns=[{"turnId": "turn-1"}],
            recent_memory_events=[{"eventId": "memory-1"}],
        )


class StubSnapshotStateBackend:
    mode = "stub_snapshot_state_backend"

    def __init__(self, root: Path) -> None:
        self.root_path = root
        self.calls: list[str] = []

    def root(self, runtime: object) -> Path:
        self.calls.append("root")
        return self.root_path

    async def prepare_self_choice(self, runtime: object) -> None:
        self.calls.append("prepare_self_choice")

    async def self_choice_private(self, runtime: object) -> dict[str, object]:
        self.calls.append("self_choice_private")
        return {"private": True}

    async def self_choice_public(self, runtime: object) -> dict[str, object]:
        self.calls.append("self_choice_public")
        return {"public": True}

    async def event_state(self, runtime: object) -> dict[str, object]:
        self.calls.append("event_state")
        return {"latest_event_id": "event-1"}

    async def active_desires(self, runtime: object, **kwargs: object) -> list[dict[str, object]]:
        self.calls.append("active_desires")
        return [{"inputs": kwargs}]

    def health_snapshot(self, runtime: object) -> dict[str, object]:
        self.calls.append("health_snapshot")
        return {"runtime_presence": {"initiative_metrics": {"observed": True}}}

    def services(self, runtime: object) -> list[dict[str, object]]:
        self.calls.append("services")
        return [{"service": "stub", "status": "ready"}]

    def xinyu_state(self, runtime: object, **kwargs: object) -> dict[str, object]:
        self.calls.append("xinyu_state")
        return {"version": 1, "received": kwargs}

    def self_action_snapshot(self, runtime: object, snapshot_func: Any) -> dict[str, object]:
        self.calls.append("self_action_snapshot")
        return snapshot_func(self.root_path)

    def private_ecosystem_snapshot(self, runtime: object, snapshot_func: Any) -> dict[str, object]:
        self.calls.append("private_ecosystem_snapshot")
        return snapshot_func(self.root_path)


def test_desktop_surface_snapshot_state_backend_contract_matches_service_manifest() -> None:
    manifest = service_contract_by_id("desktop_surface")

    assert "xinyu_bridge_desktop_surface_snapshot_state_backend.py" in manifest.contract_modules
    assert "tests/test_desktop_surface_snapshot_state_backend.py" in manifest.validation_tests
    assert manifest.process_split_ready is True
    assert "Ready for a controlled desktop_surface split" in manifest.process_split_gate


def test_snapshot_context_uses_runtime_snapshot_state_backend(tmp_path: Path) -> None:
    state_backend = StubSnapshotStateBackend(tmp_path)
    runtime = SimpleNamespace(
        **{
            DESKTOP_SURFACE_SNAPSHOT_STATE_BACKEND_RUNTIME_ATTR: state_backend,
            DESKTOP_SURFACE_PROJECTION_BACKEND_RUNTIME_ATTR: StubProjectionBackend(),
        }
    )
    entropy = SimpleNamespace(model_dump=lambda mode: {"mode": mode, "entropy": 0.2})

    context = asyncio.run(
        collect_desktop_snapshot_context(
            runtime,
            {"limit": 3},
            sample_environment_func=lambda root: {"root": str(root)},
            build_entropy_state_func=lambda **kwargs: entropy,
            read_action_digest_func=lambda root, limit: {"root": str(root), "limit": limit},
        )
    )

    assert context.event_state == {"latest_event_id": "event-1"}
    assert context.environment == {"root": str(tmp_path)}
    assert context.self_choice_public == {"public": True}
    assert context.action_digest == {"root": str(tmp_path), "limit": 5}
    assert context.initiative_metrics == {"observed": True}
    assert context.active_desires[0]["inputs"]["self_choice_state"] == {"private": True}
    assert "active_desires" in state_backend.calls


def test_desktop_snapshot_service_uses_snapshot_state_backend(monkeypatch, tmp_path: Path) -> None:
    state_backend = StubSnapshotStateBackend(tmp_path)
    runtime = SimpleNamespace(**{DESKTOP_SURFACE_SNAPSHOT_STATE_BACKEND_RUNTIME_ATTR: state_backend})

    async def collect_context(*args: object, **kwargs: object) -> DesktopSnapshotContext:
        return DesktopSnapshotContext(
            event_state={"latest_event_id": "event-9"},
            proactive_items=[{"candidateId": "candidate-1"}],
            proactive_history=[{"candidateId": "history-1"}],
            recent_turns=[{"turnId": "turn-1"}],
            recent_memory_events=[{"eventId": "memory-1"}],
            environment={"sensorQuality": "sampled"},
            entropy_state={"entropy": 0.2},
            active_desires=[{"desire": "observe"}],
            self_choice_public={"public": True},
            action_digest={"recent": []},
            health={"status": "ok"},
            initiative_metrics={"observed": True},
        )

    monkeypatch.setattr(xinyu_bridge_desktop_snapshot_service, "collect_desktop_snapshot_context", collect_context)

    snapshot = asyncio.run(
        xinyu_bridge_desktop_snapshot_service.desktop_snapshot(
            runtime,
            {},
            sample_environment_func=lambda root: {},
            build_entropy_state_func=lambda **kwargs: {},
            read_action_digest_func=lambda root, limit: {},
            self_action_snapshot_func=lambda root: {"root": str(root), "kind": "selfAction"},
            private_ecosystem_snapshot_func=lambda root: {"root": str(root), "kind": "private"},
        )
    )

    assert snapshot["lastEventId"] == "event-9"
    assert snapshot["services"] == [{"service": "stub", "status": "ready"}]
    assert snapshot["xinyuState"]["version"] == 1
    assert snapshot["selfAction"] == {"root": str(tmp_path), "kind": "selfAction"}
    assert snapshot["privateEcosystem"] == {"root": str(tmp_path), "kind": "private"}
    assert "services" in state_backend.calls
    assert "xinyu_state" in state_backend.calls


def test_memory_growth_candidates_route_uses_snapshot_state_root(monkeypatch, tmp_path: Path) -> None:
    backend = StubSnapshotStateBackend(tmp_path)
    runtime = SimpleNamespace(**{DESKTOP_SURFACE_SNAPSHOT_STATE_BACKEND_RUNTIME_ATTR: backend})
    calls: list[tuple[Path, int]] = []

    def list_growth(root: Path, *, limit: int) -> dict[str, object]:
        calls.append((root, limit))
        return {"items": [{"id": "candidate-1"}]}

    monkeypatch.setattr(xinyu_bridge_desktop_recent_routes, "list_growth_candidate_promotions", list_growth)

    result = asyncio.run(desktop_memory_growth_candidates(runtime, {"limit": 500}))

    assert result == {"items": [{"id": "candidate-1"}]}
    assert calls == [(tmp_path, 200)]


def test_snapshot_state_backend_readiness_reports_runtime_backend_mode(tmp_path: Path) -> None:
    backend = StubSnapshotStateBackend(tmp_path)
    runtime = SimpleNamespace(**{DESKTOP_SURFACE_SNAPSHOT_STATE_BACKEND_RUNTIME_ATTR: backend})

    readiness = desktop_surface_snapshot_state_backend_readiness(runtime)

    assert readiness.service_id == "desktop_surface"
    assert readiness.mode == "stub_snapshot_state_backend"
    assert readiness.ready is True
    assert "snapshot_state_backend_contract_ready" in readiness.notes
