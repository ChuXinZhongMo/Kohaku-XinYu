from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import xinyu_bridge_desktop_snapshot_service
from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_EVENT_STREAM_S3_PREFLIGHT_CONTRACT,
    DESKTOP_EVENT_STREAM_S3_PREFLIGHT_GATES,
    DESKTOP_EVENT_STREAM_S3_SATISFIED_GATES,
    DESKTOP_EVENT_STREAM_ROLLBACK,
    DESKTOP_EVENT_STREAM_REPLAY_EVENTS,
    DESKTOP_EVENT_STREAM_STATE_OWNER,
    DESKTOP_SURFACE_S3_PREFLIGHT_CONTRACT,
    DESKTOP_SURFACE_S3_PREFLIGHT_GATES,
    DESKTOP_SURFACE_S3_SATISFIED_GATES,
    DESKTOP_SURFACE_SNAPSHOT_DTO_TOP_LEVEL_KEYS,
    DESKTOP_SURFACE_FALLBACK_ADAPTER,
    DESKTOP_SURFACE_ROLLBACK,
    DESKTOP_SURFACE_STATE_OWNER,
    DesktopSurfaceHarness,
    desktop_event_stream_s3_preflight_contract,
    desktop_event_stream_readiness,
    desktop_surface_s3_preflight_contract,
    desktop_surface_capabilities,
    desktop_surface_routes,
)
from xinyu_bridge_http_dispatch_table import GET_ROUTE_DISPATCH, POST_ROUTE_DISPATCH
from xinyu_bridge_http_routes import is_known_get_route, is_known_post_route
from xinyu_desktop_service import DesktopService
from xinyu_serviceization_contracts import service_contract_by_id


def test_desktop_surface_contract_matches_service_boundary_manifest() -> None:
    contract = service_contract_by_id("desktop_surface")
    capabilities = desktop_surface_capabilities()

    assert desktop_surface_routes() == contract.api_routes
    assert tuple(capability.runtime_method for capability in capabilities) == contract.runtime_facade_methods


def test_desktop_surface_contract_matches_http_dispatch_table() -> None:
    for capability in desktop_surface_capabilities():
        if capability.http_method == "GET":
            assert is_known_get_route(capability.route)
            spec = GET_ROUTE_DISPATCH[capability.route]
        else:
            assert capability.http_method == "POST"
            assert is_known_post_route(capability.route)
            spec = POST_ROUTE_DISPATCH[capability.route]

        assert spec.method == capability.runtime_method


def test_desktop_event_stream_readiness_disabled() -> None:
    contract = service_contract_by_id("desktop_event_stream")
    readiness = desktop_event_stream_readiness(event_bus=None, ws_server=None)

    assert readiness.available is False
    assert readiness.status == "disabled"
    assert readiness.listener_url == ""
    assert readiness.service_id == "desktop_event_stream"
    assert readiness.mode == "in_process"
    assert readiness.started is False
    assert readiness.ready is False
    assert readiness.api_routes == contract.api_routes
    assert readiness.runtime_facade_methods == contract.runtime_facade_methods
    assert readiness.process_split_candidate is True
    assert readiness.process_split_ready is True
    assert readiness.process_split_gate == contract.process_split_gate
    assert readiness.state_owner == DESKTOP_EVENT_STREAM_STATE_OWNER
    assert readiness.fallback_adapter == DESKTOP_SURFACE_FALLBACK_ADAPTER
    assert readiness.rollback == DESKTOP_EVENT_STREAM_ROLLBACK
    assert DesktopService().readiness() == readiness


def test_desktop_event_stream_readiness_configured_and_ready() -> None:
    event_bus = object()
    ws_server = SimpleNamespace(host="127.0.0.1", bound_port=8765, path="/desktop", server=None)

    configured = desktop_event_stream_readiness(event_bus=event_bus, ws_server=ws_server)
    assert configured.available is True
    assert configured.status == "configured"
    assert configured.listener_url == "ws://127.0.0.1:8765/desktop"
    assert configured.started is False
    assert configured.ready is False
    assert DesktopService(event_bus=event_bus, ws_server=ws_server).readiness() == configured

    ws_server.server = object()
    ready = desktop_event_stream_readiness(event_bus=event_bus, ws_server=ws_server)
    assert ready.available is True
    assert ready.status == "ready"
    assert ready.listener_url == "ws://127.0.0.1:8765/desktop"
    assert ready.started is True
    assert ready.ready is True


def test_desktop_surface_harness_lifecycle_readiness_and_fallback() -> None:
    event_bus = object()
    ws_server = SimpleNamespace(host="127.0.0.1", bound_port=8765, path="/desktop", server=None)
    harness = DesktopSurfaceHarness(event_bus=event_bus, ws_server=ws_server)

    initial = harness.readiness()
    assert initial.service_id == "desktop_surface"
    assert initial.mode == "in_process"
    assert initial.started is False
    assert initial.ready is False
    assert initial.state_owner == DESKTOP_SURFACE_STATE_OWNER
    assert initial.fallback_adapter == DESKTOP_SURFACE_FALLBACK_ADAPTER
    assert initial.rollback == DESKTOP_SURFACE_ROLLBACK
    assert initial.event_stream.status == "configured"
    assert initial.event_stream.ready is False

    started = harness.start()
    assert started.started is True
    assert started.ready is True
    assert started.event_stream.status == "configured"

    def _method(name: str):
        def call(*args, **kwargs):
            return {"method": name, "args": args, "kwargs": kwargs}

        return call

    method_names = {capability.runtime_method for capability in desktop_surface_capabilities()}
    runtime = SimpleNamespace(**{method: _method(method) for method in method_names})
    fallback = harness.fallback_adapter(runtime)

    assert set(fallback) == method_names
    assert fallback["desktop_snapshot"]({"limit": 1})["method"] == "desktop_snapshot"

    ws_server.server = object()
    ready_stream = harness.readiness()
    assert ready_stream.ready is True
    assert ready_stream.event_stream.status == "ready"
    assert ready_stream.event_stream.ready is True

    stopped = harness.stop()
    assert stopped.started is False
    assert stopped.ready is False


def test_desktop_surface_s3_rollback_keeps_rest_surface_on_in_process_facades() -> None:
    harness = DesktopSurfaceHarness(event_bus=None, ws_server=None)

    readiness = harness.start()
    assert readiness.ready is True
    assert readiness.event_stream.available is False
    assert readiness.event_stream.rollback == DESKTOP_EVENT_STREAM_ROLLBACK
    assert readiness.rollback == DESKTOP_SURFACE_ROLLBACK

    def _method(name: str):
        def call(*args, **kwargs):
            return {"method": name, "args": args, "kwargs": kwargs}

        return call

    method_names = {capability.runtime_method for capability in desktop_surface_capabilities()}
    runtime = SimpleNamespace(**{method: _method(method) for method in method_names})
    fallback = harness.fallback_adapter(runtime)

    assert set(fallback) == method_names
    assert fallback["desktop_snapshot"]({})["method"] == "desktop_snapshot"
    assert fallback["desktop_events_recent"]({"limit": 5})["method"] == "desktop_events_recent"
    assert fallback["desktop_self_action_approval"]({"approved": True})["method"] == "desktop_self_action_approval"


def test_desktop_surface_s3_preflight_contract_tracks_current_progress() -> None:
    contract = desktop_surface_s3_preflight_contract()

    assert contract.service_id == "desktop_surface"
    assert contract.ready is True
    assert contract.required_gates == DESKTOP_SURFACE_S3_PREFLIGHT_GATES
    assert contract.satisfied_gates == DESKTOP_SURFACE_S3_SATISFIED_GATES
    assert contract.missing_gates == ()
    assert contract.snapshot_top_level_keys == DESKTOP_SURFACE_SNAPSHOT_DTO_TOP_LEVEL_KEYS
    assert contract.event_stream_replay_events == DESKTOP_EVENT_STREAM_REPLAY_EVENTS
    assert contract.rollback == DESKTOP_SURFACE_ROLLBACK
    assert "route_backend_selection_ready" in contract.notes
    assert "snapshot_projection_backend_ready" in contract.notes
    assert "self_action_approval_backend_ready" in contract.notes
    assert "snapshot_state_backend_ready" in contract.notes


def test_desktop_surface_s3_preflight_constants_match_factory_defaults() -> None:
    assert desktop_surface_s3_preflight_contract() == DESKTOP_SURFACE_S3_PREFLIGHT_CONTRACT
    assert desktop_event_stream_s3_preflight_contract() == DESKTOP_EVENT_STREAM_S3_PREFLIGHT_CONTRACT


def test_desktop_surface_s3_preflight_contract_tracks_missing_gates() -> None:
    contract = desktop_surface_s3_preflight_contract(
        (
            "route_backend_selection_contract",
            "projection_backend_contract",
            "self_action_approval_backend_contract",
            "snapshot_state_backend_contract",
            "snapshot_dto_stability_contract",
            "websocket_lifecycle_contract",
            "not_a_gate",
        )
    )

    assert contract.ready is False
    assert contract.satisfied_gates == (
        "route_backend_selection_contract",
        "projection_backend_contract",
        "self_action_approval_backend_contract",
        "snapshot_state_backend_contract",
        "websocket_lifecycle_contract",
        "snapshot_dto_stability_contract",
    )
    assert "not_a_gate" not in contract.satisfied_gates
    assert "event_replay_contract" in contract.missing_gates
    assert "backpressure_contract" in contract.missing_gates


def test_desktop_surface_s3_preflight_contract_requires_all_gates() -> None:
    contract = desktop_surface_s3_preflight_contract(DESKTOP_SURFACE_S3_PREFLIGHT_GATES)

    assert contract.ready is True
    assert contract.satisfied_gates == DESKTOP_SURFACE_S3_PREFLIGHT_GATES
    assert contract.missing_gates == ()


def test_desktop_event_stream_s3_preflight_contract_is_ready_without_snapshot_surface() -> None:
    contract = desktop_event_stream_s3_preflight_contract()

    assert contract.service_id == "desktop_event_stream"
    assert contract.ready is True
    assert contract.required_gates == DESKTOP_EVENT_STREAM_S3_PREFLIGHT_GATES
    assert contract.satisfied_gates == DESKTOP_EVENT_STREAM_S3_SATISFIED_GATES
    assert contract.missing_gates == ()
    assert contract.event_stream_replay_events == DESKTOP_EVENT_STREAM_REPLAY_EVENTS
    assert contract.rollback == DESKTOP_EVENT_STREAM_ROLLBACK
    assert "event_stream_boundary_only" in contract.notes
    assert "snapshot_projection_and_self_action_remain_in_desktop_surface" in contract.notes


def test_desktop_event_stream_s3_preflight_contract_tracks_missing_gates() -> None:
    contract = desktop_event_stream_s3_preflight_contract(("websocket_lifecycle_contract",))

    assert contract.ready is False
    assert contract.satisfied_gates == ("websocket_lifecycle_contract",)
    assert "event_replay_contract" in contract.missing_gates
    assert "backpressure_contract" in contract.missing_gates


def test_desktop_surface_snapshot_dto_contract_stable_top_level_shape(monkeypatch, tmp_path: Path) -> None:
    async def collect_context(*args, **kwargs):
        return SimpleNamespace(
            event_state={"version": 1, "available": True, "latest_event_id": "event-3"},
            health={"status": "ok"},
            environment={"sensorQuality": "sampled"},
            entropy_state={"entropy_level": 0.2},
            self_choice_public={"status": "idle"},
            active_desires=[],
            proactive_items=[],
            proactive_history=[],
            recent_turns=[],
            recent_memory_events=[],
            action_digest={"recent": []},
            initiative_metrics={"observed": True},
        )

    monkeypatch.setattr(xinyu_bridge_desktop_snapshot_service, "collect_desktop_snapshot_context", collect_context)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _desktop_services=lambda: [
            {"service": "core", "status": "ready"},
            {"service": "desktop_events", "status": "ready"},
        ],
        _desktop_xinyu_state=lambda **kwargs: {"version": 1, "recentTurnCount": len(kwargs["recent_turns"])},
    )

    snapshot = asyncio.run(
        xinyu_bridge_desktop_snapshot_service.desktop_snapshot(
            runtime,
            {},
            sample_environment_func=lambda *args, **kwargs: {},
            build_entropy_state_func=lambda *args, **kwargs: {},
            read_action_digest_func=lambda *args, **kwargs: {},
            self_action_snapshot_func=lambda root: {"version": 1, "queue": []},
            private_ecosystem_snapshot_func=lambda root: {"version": 1, "enabled": False},
        )
    )

    assert tuple(snapshot) == (
        "version",
        "snapshotAt",
        "lastEventId",
        "services",
        "health",
        "environment",
        "entropyState",
        "selfChoiceState",
        "activeDesires",
        "xinyuState",
        "eventBus",
        "proactiveInbox",
        "proactiveHistory",
        "recentTurns",
        "recentMemoryEvents",
        "actionDigestState",
        "selfAction",
        "privateEcosystem",
        "notes",
    )
    assert snapshot["version"] == 1
    assert snapshot["lastEventId"] == "event-3"
    assert snapshot["eventBus"] == {"version": 1, "available": True, "latest_event_id": "event-3"}
    assert snapshot["services"][1] == {"service": "desktop_events", "status": "ready"}
    assert snapshot["selfAction"] == {"version": 1, "queue": []}
    assert snapshot["privateEcosystem"] == {"version": 1, "enabled": False}
    for key in DESKTOP_SURFACE_SNAPSHOT_DTO_TOP_LEVEL_KEYS:
        assert key in snapshot
