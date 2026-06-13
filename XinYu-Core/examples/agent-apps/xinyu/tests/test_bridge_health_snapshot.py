from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import xinyu_bridge_health_snapshot
from xinyu_bridge_health_snapshot import health_snapshot, runtime_health, runtime_health_snapshot
from xinyu_bridge_health_snapshot_service import (
    HealthDiagnosticsRuntimeContext,
    build_health_snapshot_from_context,
    build_operator_health,
    health_diagnostics_runtime_context,
)
from xinyu_bridge_health_diagnostics_service import (
    HEALTH_DIAGNOSTICS_CAPABILITIES,
    HEALTH_DIAGNOSTICS_FALLBACK_ADAPTER,
    HEALTH_DIAGNOSTICS_INJECTED_DEPENDENCIES,
    HEALTH_DIAGNOSTICS_ROLLBACK,
    HEALTH_DIAGNOSTICS_RUNTIME_INTERNAL_FIELDS,
    HEALTH_DIAGNOSTICS_S3_PREFLIGHT_GATES,
    HEALTH_DIAGNOSTICS_S3_SATISFIED_GATES,
    HEALTH_DIAGNOSTICS_STATE_OWNER,
    HealthDiagnosticsDeps,
    HealthDiagnosticsService,
    HealthDiagnosticsServiceHealthProvider,
    aggregate_service_health,
    build_health_diagnostics_service,
    health_diagnostics_preflight_contract,
    health_diagnostics_service_health_contract,
)
from xinyu_bridge_health_provider_registry import (
    HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_HTTP_MODE,
    HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_IN_PROCESS_MODE,
    HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_ROLLBACK,
    HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR,
    HttpHealthDiagnosticsProviderRegistry,
    health_diagnostics_provider_registry_readiness,
)
from xinyu_bridge_codex_execution_contract import CODEX_EXECUTION_ROLLBACK, CODEX_EXECUTION_STATE_OWNER
from xinyu_bridge_desktop_surface_route_backend import DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR
from xinyu_bridge_desktop_surface_service import (
    DESKTOP_SURFACE_SERVICE_CONFIG_BACKEND_ENV,
    DESKTOP_SURFACE_SERVICE_CONFIG_ENDPOINT_ENV,
    DESKTOP_SURFACE_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
)
from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_EVENT_STREAM_EXTERNALIZATION_SCOPE,
    DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY,
    DESKTOP_EVENT_STREAM_ROLLBACK,
    DESKTOP_EVENT_STREAM_RUNTIME_ATTR,
    DESKTOP_EVENT_STREAM_STATE_OWNER,
    DESKTOP_SURFACE_ROLLBACK,
    DESKTOP_SURFACE_STATE_OWNER,
    desktop_event_stream_readiness,
)
from xinyu_bridge_external_action_backend import EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR
from xinyu_bridge_external_action_contract import EXTERNAL_ACTION_ROLLBACK, EXTERNAL_ACTION_STATE_OWNER
from xinyu_bridge_external_action_service import (
    EXTERNAL_ACTION_SERVICE_CONFIG_BACKEND_ENV,
    EXTERNAL_ACTION_SERVICE_CONFIG_DRY_RUN_ENV,
    EXTERNAL_ACTION_SERVICE_CONFIG_ENDPOINT_ENV,
)
from xinyu_bridge_health_service_providers import (
    chat_turn_service_health,
    codex_execution_service_health,
    desktop_event_stream_service_health,
    desktop_surface_service_health,
    external_action_service_health,
    health_diagnostics_default_service_health_providers,
    health_diagnostics_service_health,
    learning_ingest_service_health,
    life_metabolism_service_health,
    memory_governance_reports_service_health,
    proactive_delivery_service_health,
    service_health_provider_ids,
)
from xinyu_bridge_learning_ingest_route_backend import LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR
from xinyu_bridge_learning_ingest_service import (
    LEARNING_INGEST_SERVICE_CONFIG_BACKEND_ENV,
    LEARNING_INGEST_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
)
from xinyu_bridge_proactive_delivery_contract import PROACTIVE_DELIVERY_STATE_OWNER
from xinyu_bridge_proactive_delivery_route_backend import PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR
from xinyu_bridge_proactive_delivery_service import (
    PROACTIVE_DELIVERY_SERVICE_CONFIG_BACKEND_ENV,
    PROACTIVE_DELIVERY_SERVICE_CONFIG_ENDPOINT_ENV,
    PROACTIVE_DELIVERY_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
)
from xinyu_serviceization_contracts import service_boundary_contracts, service_contract_by_id
from xinyu_serviceization_contracts import process_split_ready_contracts


class _SelfChoiceStore:
    def health_snapshot(self) -> dict[str, object]:
        return {"available": True}


def _runtime(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        xinyu_dir=root,
        bridge_version="runtime-version",
        bridge_source_digest="runtime-bridge-digest",
        bridge_runtime_source_digest="runtime-source-digest",
        memory_root=root / "memory",
        _sessions={},
        turn_timeout_seconds=1,
        pre_model_routes_timeout_seconds=1,
        outward_renderer=False,
        renderer_mode="off",
        render_timeout_seconds=1,
        session_idle_ttl_seconds=60,
        max_sessions=2,
        dialogue_prompt_tail_entries=0,
        dialogue_session_tail_entries=0,
        dialogue_persisted_tail_entries=0,
        proactive_min_interval_seconds=60,
        autonomous_maintenance_enabled=False,
        _autonomous_task=None,
        _autonomous_in_progress=False,
        autonomous_maintenance_session_key="",
        autonomous_maintenance_initial_delay_seconds=0,
        autonomous_maintenance_interval_seconds=0,
        _autonomous_run_count=0,
        _autonomous_failure_count=0,
        _autonomous_last_started_at="",
        _autonomous_last_success_at="",
        _autonomous_last_error="",
        _autonomous_last_memory_changed=False,
        _autonomous_next_run_at="",
        _metabolism_task=None,
        _metabolism_in_progress=False,
        metabolism_runner_interval_seconds=0,
        _metabolism_run_count=0,
        _metabolism_last_started_at="",
        _metabolism_last_success_at="",
        _metabolism_last_error="",
        _v1_health=lambda: {"enabled": False},
        self_choice_store=_SelfChoiceStore(),
        _closed=False,
    )


def test_health_snapshot_does_not_initialize_code_awareness_files(tmp_path: Path) -> None:
    result = health_snapshot(
        _runtime(tmp_path),
        bridge_version="test",
        source_digest="running-bridge",
        runtime_source_digest="running-runtime",
    )

    assert result["ok"] is True
    assert result["code_awareness"]["available"] is False
    assert result["service_health"]["service_health_status"] == "ok"
    assert not (tmp_path / "runtime/code_awareness/source_snapshot.json").exists()
    assert not (tmp_path / "memory/context/code_change_awareness_state.md").exists()


def test_runtime_health_wrappers_use_runtime_version_and_digests(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)

    snapshot = runtime_health_snapshot(runtime)
    health = asyncio.run(runtime_health(runtime))

    assert snapshot["version"] == "runtime-version"
    assert snapshot["source_digest"] == "runtime-bridge-digest"
    assert snapshot["runtime_source_digest"] == "runtime-source-digest"
    assert health["version"] == "runtime-version"
    assert health["source_digest"] == "runtime-bridge-digest"


def test_health_snapshot_prefers_runtime_service_handle(tmp_path: Path) -> None:
    calls: list[tuple[str, object]] = []

    class _HealthService:
        def health_snapshot(self, runtime: object, **kwargs: object) -> dict[str, object]:
            calls.append(("service", runtime))
            return {"ok": True, "source": "runtime_service", **kwargs}

    runtime = _runtime(tmp_path)
    runtime._health_diagnostics_service = _HealthService()

    result = health_snapshot(
        runtime,
        bridge_version="test",
        source_digest="bridge-digest",
        runtime_source_digest="runtime-digest",
    )

    assert result == {
        "ok": True,
        "source": "runtime_service",
        "bridge_version": "test",
        "source_digest": "bridge-digest",
        "runtime_source_digest": "runtime-digest",
    }
    assert calls == [("service", runtime)]


def test_health_snapshot_uses_facade_reader_dependencies(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        xinyu_bridge_health_snapshot,
        "read_code_awareness_summary",
        lambda root: calls.append(("code", root)) or {"available": True},
    )
    monkeypatch.setattr(
        xinyu_bridge_health_snapshot,
        "read_runtime_presence_summary",
        lambda root: calls.append(("presence", root)) or {"current_turn_state": "running"},
    )
    monkeypatch.setattr(
        xinyu_bridge_health_snapshot,
        "read_turn_route_summary",
        lambda root: calls.append(("route", root)) or {"last_stage": "model", "last_status": "ok"},
    )
    monkeypatch.setattr(
        xinyu_bridge_health_snapshot,
        "read_recent_action_digest_snapshot",
        lambda root, *, limit: calls.append(("digest", (root, limit))) or {"recent": []},
    )

    result = health_snapshot(
        _runtime(tmp_path),
        bridge_version="test",
        source_digest="bridge-digest",
        runtime_source_digest="runtime-digest",
    )

    assert result["code_awareness"]["running_bridge_digest"] == "bridge-digest"
    assert result["operator"]["current_turn_state"] == "running"
    assert set(result["service_health"]["services"]) == set(service_health_provider_ids())
    assert calls == [
        ("code", tmp_path),
        ("presence", tmp_path),
        ("route", tmp_path),
        ("digest", (tmp_path, 3)),
    ]


def test_health_snapshot_runtime_context_preserves_payload_shape(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime._sessions = {"s1": object(), "s2": object()}
    context = health_diagnostics_runtime_context(runtime)

    assert context == HealthDiagnosticsRuntimeContext(
        xinyu_dir=tmp_path,
        memory_root=tmp_path / "memory",
        sessions=2,
        turn_timeout_seconds=1,
        pre_model_routes_timeout_seconds=1,
        outward_renderer=False,
        renderer_mode="off",
        render_timeout_seconds=1,
        session_idle_ttl_seconds=60,
        max_sessions=2,
        dialogue_prompt_tail_entries=0,
        dialogue_session_tail_entries=0,
        dialogue_persisted_tail_entries=0,
        proactive_min_interval_seconds=60,
        v1={"enabled": False},
        self_choice={"available": True},
        closed=False,
    )

    result = build_health_snapshot_from_context(
        context,
        bridge_version="context-version",
        source_digest="bridge-digest",
        runtime_source_digest="runtime-digest",
        code_awareness={"available": False},
        runtime_presence={"program_awareness": {"ok": True}},
        turn_route={"last_stage": "none"},
        autonomous_maintenance={"enabled": False},
        operator={"current_turn_state": "idle"},
        metabolism={"task_running": False},
        action_experience_digest={"recent": []},
    )

    assert result["version"] == "context-version"
    assert result["xinyu_dir"] == str(tmp_path)
    assert result["memory_root"] == str(tmp_path / "memory")
    assert result["sessions"] == 2
    assert result["dialogue_memory"] == {
        "prompt_tail_entries": 0,
        "session_tail_entries": 0,
        "persisted_tail_entries": 0,
    }
    assert result["program_awareness"] == {"ok": True}
    assert result["v1"] == {"enabled": False}
    assert result["self_choice"] == {"available": True}
    assert "service_health" not in result
    assert result["closed"] is False


def test_default_service_health_providers_are_side_effect_free(tmp_path: Path) -> None:
    class Runtime:
        def health_snapshot(self) -> dict[str, object]:
            raise AssertionError("service health providers must not call runtime health_snapshot")

    runtime = Runtime()
    providers = health_diagnostics_default_service_health_providers(runtime)
    summary = aggregate_service_health(providers, runtime)

    assert tuple(provider.service_id for provider in providers) == service_health_provider_ids()
    assert summary["service_health_status"] == "ok"
    assert summary["service_count"] == len(service_health_provider_ids())
    assert summary["degraded_count"] == 0
    assert set(summary["services"]) == set(service_health_provider_ids())
    assert not (tmp_path / "runtime").exists()
    assert not (tmp_path / "memory").exists()


def test_service_health_provider_ids_cover_serviceization_contracts() -> None:
    assert set(service_health_provider_ids()) == {
        contract.service_id for contract in service_boundary_contracts()
    }


def test_split_ready_service_health_payloads_expose_manifest_metadata() -> None:
    providers = {
        provider.service_id: provider
        for provider in health_diagnostics_default_service_health_providers(SimpleNamespace())
    }

    for contract in process_split_ready_contracts():
        health = providers[contract.service_id].health_func(SimpleNamespace())
        payload = health["payload"]
        service_payload = payload.get("service") if isinstance(payload, dict) else None
        if isinstance(service_payload, dict) and service_payload.get("service_id") == contract.service_id:
            payload = service_payload

        assert payload["api_routes"] == contract.api_routes, contract.service_id
        assert payload["runtime_facade_methods"] == contract.runtime_facade_methods, contract.service_id
        assert payload["process_split_candidate"] is contract.process_split_candidate, contract.service_id
        assert payload["process_split_ready"] is contract.process_split_ready, contract.service_id


def test_health_snapshot_service_health_aggregates_split_ready_metadata(tmp_path: Path) -> None:
    result = health_snapshot(
        _runtime(tmp_path),
        bridge_version="test",
        source_digest="bridge-digest",
        runtime_source_digest="runtime-digest",
    )
    services = result["service_health"]["services"]
    process_split_gate_payloads = {
        "codex_execution",
        "desktop_event_stream",
        "health_diagnostics",
    }
    expected_state_owners = {
        "codex_execution": CODEX_EXECUTION_STATE_OWNER,
        "desktop_event_stream": DESKTOP_EVENT_STREAM_STATE_OWNER,
        "desktop_surface": DESKTOP_SURFACE_STATE_OWNER,
        "external_action": EXTERNAL_ACTION_STATE_OWNER,
        "health_diagnostics": HEALTH_DIAGNOSTICS_STATE_OWNER,
        "proactive_delivery": PROACTIVE_DELIVERY_STATE_OWNER,
    }

    for contract in process_split_ready_contracts():
        service_health = services[contract.service_id]
        payload = service_health["payload"]
        service_payload = payload.get("service") if isinstance(payload, dict) else None
        if isinstance(service_payload, dict) and service_payload.get("service_id") == contract.service_id:
            payload = service_payload

        assert service_health["service_id"] == contract.service_id
        assert payload["api_routes"] == contract.api_routes, contract.service_id
        assert payload["runtime_facade_methods"] == contract.runtime_facade_methods, contract.service_id
        assert payload["process_split_candidate"] is True, contract.service_id
        assert payload["process_split_ready"] is True, contract.service_id
        assert payload["state_owner"] == expected_state_owners[contract.service_id], contract.service_id
        assert payload["fallback_adapter"], contract.service_id
        assert payload["rollback"], contract.service_id
        assert ("process_split_gate" in payload) is (
            contract.service_id in process_split_gate_payloads
        ), contract.service_id
        if contract.service_id in process_split_gate_payloads:
            assert payload["process_split_gate"] == contract.process_split_gate


def test_chat_turn_service_health_exposes_local_control_plane_routes() -> None:
    contract = service_contract_by_id("chat_turn")
    health = chat_turn_service_health(SimpleNamespace())

    assert health["service_id"] == "chat_turn"
    assert health["ok"] is True
    assert health["payload"]["api_routes"] == contract.api_routes
    assert health["payload"]["runtime_facade_methods"] == contract.runtime_facade_methods
    assert health["payload"]["execution_routes"] == ("/chat",)
    assert health["payload"]["control_plane_routes"] == contract.api_routes[1:]
    assert health["payload"]["token_required_routes"] == (
        "/internal/message/ack",
        "/internal/message/drop",
    )
    assert "control_plane_routes_remain_in_process" in health["notes"]


def test_memory_governance_service_health_exposes_token_required_control_plane() -> None:
    contract = service_contract_by_id("memory_governance_reports")
    health = memory_governance_reports_service_health(SimpleNamespace())

    assert health["service_id"] == "memory_governance_reports"
    assert health["ok"] is True
    assert health["payload"]["local_route_control_plane"] is True
    assert health["payload"]["control_plane_routes"] == contract.api_routes
    assert health["payload"]["token_required_routes"] == contract.api_routes
    assert health["payload"]["control_plane_requires_bridge_token"] is True
    assert "token_required_route_control_plane" in health["notes"]


def test_learning_ingest_service_health_exposes_sticker_local_utility_route() -> None:
    contract = service_contract_by_id("learning_ingest")
    health = learning_ingest_service_health(SimpleNamespace())

    assert health["service_id"] == "learning_ingest"
    assert health["ok"] is True
    assert health["payload"]["api_routes"] == contract.api_routes
    assert health["payload"]["runtime_facade_methods"] == contract.runtime_facade_methods
    assert health["payload"]["process_split_ready"] is False
    assert health["payload"]["local_utility_routes"] == ("/sticker/import",)
    assert "/sticker/import" not in health["payload"]["route_backend_routes"]
    assert health["payload"]["backend_config_env"] == LEARNING_INGEST_SERVICE_CONFIG_BACKEND_ENV
    assert health["payload"]["route_backend_config_env"] == LEARNING_INGEST_SERVICE_CONFIG_ROUTE_BACKEND_ENV
    assert health["payload"]["route_backend_enabled"] is False
    assert health["payload"]["route_backend_runtime_attr"] == LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR
    assert "local_utility_routes_remain_in_process" in health["notes"]


def test_life_metabolism_service_health_exposes_dynamic_ticket_routes() -> None:
    contract = service_contract_by_id("life_metabolism")
    health = life_metabolism_service_health(SimpleNamespace())

    assert health["service_id"] == "life_metabolism"
    assert health["ok"] is True
    assert health["payload"]["api_routes"] == contract.api_routes
    assert health["payload"]["runtime_facade_methods"] == contract.runtime_facade_methods
    assert health["payload"]["dynamic_ticket_routes"] is True
    assert "/life/metabolism/tickets/{ticket_id}/approve" in health["payload"]["ticket_action_routes"]
    assert "dynamic_ticket_routes_remain_in_process" in health["notes"]


def test_desktop_event_stream_service_health_exposes_split_ready_contract_metadata() -> None:
    contract = service_contract_by_id("desktop_event_stream")
    health = desktop_event_stream_service_health(SimpleNamespace())

    assert health["service_id"] == "desktop_event_stream"
    assert health["ok"] is True
    assert health["payload"]["api_routes"] == contract.api_routes
    assert health["payload"]["runtime_facade_methods"] == contract.runtime_facade_methods
    assert health["payload"]["process_split_candidate"] is True
    assert health["payload"]["process_split_ready"] is True
    assert health["payload"]["state_owner"] == DESKTOP_EVENT_STREAM_STATE_OWNER
    assert health["payload"]["rollback"] == DESKTOP_EVENT_STREAM_ROLLBACK
    assert health["payload"]["runtime_attr"] == DESKTOP_EVENT_STREAM_RUNTIME_ATTR
    assert health["payload"]["lifecycle_boundary"] == DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY
    assert health["payload"]["externalization_scope"] == DESKTOP_EVENT_STREAM_EXTERNALIZATION_SCOPE
    assert health["payload"]["app_owned_lifecycle"] is True


def test_desktop_event_stream_health_contract_only_fallback_is_distinct_from_runtime_stream_readiness() -> None:
    direct = desktop_event_stream_readiness(event_bus=None, ws_server=None)
    health = desktop_event_stream_service_health(SimpleNamespace())

    assert direct.ready is False
    assert direct.status == "disabled"
    assert health["ok"] is True
    assert health["payload"]["ready"] is True
    assert health["payload"]["status"] == "contract_only"
    assert "app_level_ws_lifecycle_not_started_by_runtime" in health["notes"]


def test_codex_execution_service_health_exposes_split_ready_contract_metadata() -> None:
    contract = service_contract_by_id("codex_execution")
    health = codex_execution_service_health(SimpleNamespace())
    service = health["payload"]["service"]

    assert health["service_id"] == "codex_execution"
    assert health["ok"] is True
    assert service["api_routes"] == contract.api_routes
    assert service["runtime_facade_methods"] == contract.runtime_facade_methods
    assert service["process_split_candidate"] is True
    assert service["process_split_ready"] is True
    assert service["process_split_gate"] == contract.process_split_gate
    assert service["state_owner"] == CODEX_EXECUTION_STATE_OWNER
    assert service["rollback"] == CODEX_EXECUTION_ROLLBACK
    assert service["worker_enabled"] is False
    assert service["worker_healthy"] is True
    assert service["fallback_on_unhealthy"] is True
    assert service["submit_timeout_seconds"] == 30


def test_desktop_surface_service_health_exposes_split_ready_contract_metadata() -> None:
    contract = service_contract_by_id("desktop_surface")
    health = desktop_surface_service_health(SimpleNamespace())

    assert health["service_id"] == "desktop_surface"
    assert health["ok"] is True
    assert health["payload"]["api_routes"] == contract.api_routes
    assert health["payload"]["runtime_facade_methods"] == contract.runtime_facade_methods
    assert health["payload"]["process_split_candidate"] is True
    assert health["payload"]["process_split_ready"] is True
    assert health["payload"]["state_owner"] == DESKTOP_SURFACE_STATE_OWNER
    assert health["payload"]["rollback"] == DESKTOP_SURFACE_ROLLBACK
    assert health["payload"]["backend_config_env"] == DESKTOP_SURFACE_SERVICE_CONFIG_BACKEND_ENV
    assert health["payload"]["route_backend_config_env"] == DESKTOP_SURFACE_SERVICE_CONFIG_ROUTE_BACKEND_ENV
    assert health["payload"]["endpoint_config_env"] == DESKTOP_SURFACE_SERVICE_CONFIG_ENDPOINT_ENV
    assert health["payload"]["endpoint"] == ""
    assert health["payload"]["route_backend_enabled"] is False
    assert health["payload"]["route_backend_runtime_attr"] == DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR


def test_external_action_service_health_exposes_split_ready_contract_metadata() -> None:
    contract = service_contract_by_id("external_action")
    health = external_action_service_health(SimpleNamespace())
    service = health["payload"]["service"]

    assert health["service_id"] == "external_action"
    assert health["ok"] is True
    assert service["api_routes"] == contract.api_routes
    assert service["runtime_facade_methods"] == contract.runtime_facade_methods
    assert service["process_split_candidate"] is True
    assert service["process_split_ready"] is True
    assert service["state_owner"] == EXTERNAL_ACTION_STATE_OWNER
    assert service["rollback"] == EXTERNAL_ACTION_ROLLBACK
    assert service["backend_config_env"] == EXTERNAL_ACTION_SERVICE_CONFIG_BACKEND_ENV
    assert service["dry_run_config_env"] == EXTERNAL_ACTION_SERVICE_CONFIG_DRY_RUN_ENV
    assert service["endpoint_config_env"] == EXTERNAL_ACTION_SERVICE_CONFIG_ENDPOINT_ENV
    assert service["endpoint"] == ""
    assert service["backend_enabled"] is False
    assert service["backend_runtime_attr"] == EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR
    assert service["backend_rollback"] == health["payload"]["backend"]["rollback"]


def test_external_action_health_fallback_ok_is_distinct_from_external_backend_readiness() -> None:
    health = external_action_service_health(SimpleNamespace())
    service = health["payload"]["service"]
    backend = health["payload"]["backend"]

    assert health["ok"] is True
    assert health["ready"] is True
    assert service["ready"] is False
    assert service["backend_enabled"] is False
    assert backend["ready"] is False
    assert "service_owned_in_process_harness" in health["notes"]


def test_health_diagnostics_service_health_exposes_split_ready_contract_metadata() -> None:
    contract = service_contract_by_id("health_diagnostics")
    health = health_diagnostics_service_health(SimpleNamespace())

    assert health["service_id"] == "health_diagnostics"
    assert health["ok"] is True
    assert health["payload"]["api_routes"] == contract.api_routes
    assert health["payload"]["runtime_facade_methods"] == contract.runtime_facade_methods
    assert health["payload"]["process_split_candidate"] is True
    assert health["payload"]["process_split_ready"] is True
    assert health["payload"]["process_split_gate"] == contract.process_split_gate
    assert health["payload"]["state_owner"] == HEALTH_DIAGNOSTICS_STATE_OWNER
    assert health["payload"]["rollback"] == HEALTH_DIAGNOSTICS_ROLLBACK


def test_proactive_delivery_service_health_exposes_service_contract_metadata() -> None:
    contract = service_contract_by_id("proactive_delivery")
    health = proactive_delivery_service_health(SimpleNamespace())

    assert health["service_id"] == "proactive_delivery"
    assert health["ok"] is True
    assert health["payload"]["service"]["api_routes"] == contract.api_routes
    assert health["payload"]["service"]["runtime_facade_methods"] == contract.runtime_facade_methods
    assert health["payload"]["service"]["process_split_candidate"] is True
    assert health["payload"]["service"]["process_split_ready"] is True
    assert health["payload"]["service"]["backend_config_env"] == PROACTIVE_DELIVERY_SERVICE_CONFIG_BACKEND_ENV
    assert health["payload"]["service"]["route_backend_config_env"] == PROACTIVE_DELIVERY_SERVICE_CONFIG_ROUTE_BACKEND_ENV
    assert health["payload"]["service"]["endpoint_config_env"] == PROACTIVE_DELIVERY_SERVICE_CONFIG_ENDPOINT_ENV
    assert health["payload"]["service"]["endpoint"] == ""
    assert health["payload"]["service"]["route_backend_enabled"] is False
    assert health["payload"]["service"]["route_backend_runtime_attr"] == PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR
    assert health["payload"]["transport_preflight"]["ready"] is True
    assert "transport_contracts_ready_for_controlled_process_split" in health["notes"]


def test_health_diagnostics_service_provider_reads_runtime_handle_readiness(tmp_path: Path) -> None:
    service = build_health_diagnostics_service(
        HealthDiagnosticsDeps(
            read_code_awareness_summary_func=lambda root: {"available": False},
            read_runtime_presence_summary_func=lambda root: {"current_turn_state": "idle"},
            read_turn_route_summary_func=lambda root: {"last_stage": "none", "last_status": "ok"},
            read_recent_action_digest_snapshot_func=lambda root, *, limit: {"recent": []},
            autonomous_maintenance_health_func=lambda runtime: {"enabled": False},
            metabolism_health_func=lambda runtime: {"task_running": False},
            operator_health_func=lambda **kwargs: {"current_turn_state": "idle"},
        )
    )
    runtime = _runtime(tmp_path)
    runtime._health_diagnostics_service = service

    before_start = aggregate_service_health(health_diagnostics_default_service_health_providers(runtime), runtime)
    service.start()
    after_start = aggregate_service_health(health_diagnostics_default_service_health_providers(runtime), runtime)

    assert before_start["services"]["health_diagnostics"]["status"] == "degraded"
    assert before_start["services"]["health_diagnostics"]["ok"] is False
    assert before_start["services"]["health_diagnostics"]["payload"]["ready"] is False
    assert after_start["services"]["health_diagnostics"]["status"] == "ok"
    assert after_start["services"]["health_diagnostics"]["ok"] is True
    assert after_start["services"]["health_diagnostics"]["payload"]["ready"] is True


def test_health_provider_registry_defaults_and_runtime_override() -> None:
    class Registry:
        mode = "external_provider_registry_dry_run"

        def __init__(self) -> None:
            self.calls = 0

        def providers(self, runtime: object) -> tuple[HealthDiagnosticsServiceHealthProvider, ...]:
            self.calls += 1
            return (
                HealthDiagnosticsServiceHealthProvider(
                    "health_diagnostics",
                    lambda received_runtime: {
                        "ok": True,
                        "ready": True,
                        "status": "ok",
                        "mode": "external_provider_registry_dry_run",
                        "notes": ["external-registry"],
                    },
                ),
            )

    runtime = SimpleNamespace()
    fallback = health_diagnostics_provider_registry_readiness(runtime)
    assert fallback.mode == HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_IN_PROCESS_MODE
    assert fallback.enabled is True
    assert fallback.ready is True
    assert fallback.endpoint == ""
    assert fallback.rollback == HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_ROLLBACK
    assert fallback.runtime_attr == HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR
    assert fallback.contract_rollback == HEALTH_DIAGNOSTICS_ROLLBACK
    assert fallback.provider_count == len(service_health_provider_ids())

    registry = Registry()
    setattr(runtime, HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR, registry)
    overridden = health_diagnostics_provider_registry_readiness(runtime)

    assert overridden.mode == "external_provider_registry_dry_run"
    assert overridden.enabled is True
    assert overridden.ready is True
    assert overridden.endpoint == ""
    assert overridden.runtime_attr == HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR
    assert overridden.contract_rollback == HEALTH_DIAGNOSTICS_ROLLBACK
    assert overridden.provider_count == 1
    assert registry.calls == 1


def test_health_provider_registry_http_adapter_uses_transport() -> None:
    calls: list[tuple[str, str, int]] = []

    def transport(method: str, url: str, timeout_seconds: int) -> dict[str, object]:
        calls.append((method, url, timeout_seconds))
        service_id = url.rsplit("/", 1)[-1]
        return {
            "service_id": service_id,
            "ok": True,
            "ready": True,
            "status": "ok",
            "payload": {"source": "http"},
            "notes": ("http_provider",),
        }

    registry = HttpHealthDiagnosticsProviderRegistry(
        endpoint="http://127.0.0.1:8787/",
        enabled=True,
        provider_ids=("codex_execution", "health_diagnostics"),
        timeout_seconds=3,
        transport=transport,
    )
    runtime = SimpleNamespace()
    readiness = health_diagnostics_provider_registry_readiness(runtime, explicit_registry=registry)
    summary = aggregate_service_health(
        registry.providers(runtime),
        runtime,
        required_service_ids=("codex_execution", "health_diagnostics"),
    )

    assert readiness.mode == HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_HTTP_MODE
    assert readiness.enabled is True
    assert readiness.ready is True
    assert readiness.endpoint == "http://127.0.0.1:8787"
    assert readiness.provider_count == 2
    assert summary["ok"] is True
    assert summary["services"]["codex_execution"]["payload"] == {"source": "http"}
    assert summary["services"]["health_diagnostics"]["notes"] == ("http_provider",)
    assert calls == [
        ("GET", "http://127.0.0.1:8787/health/services/codex_execution", 3),
        ("GET", "http://127.0.0.1:8787/health/services/health_diagnostics", 3),
    ]


def test_build_operator_health_preserves_current_payload_shape() -> None:
    result = build_operator_health(
        runtime_presence={
            "current_turn_state": "running",
            "current_turn_age_seconds": "305",
            "stale_running": True,
        },
        turn_route={
            "last_stage": "model_inject_started",
            "last_route": "slow_live",
            "last_status": "running",
            "last_timeout_stage": "sidecar",
            "last_timeout_reason": "slow",
        },
    )

    assert result == {
        "current_turn_state": "running",
        "current_turn_age_seconds": 305,
        "route_stage": "model_inject_started",
        "route": "slow_live",
        "route_status": "running",
        "stale_running": True,
        "stale_age_seconds": 5,
        "last_timeout_stage": "sidecar",
        "last_timeout_reason": "slow",
    }


def test_health_diagnostics_capabilities_match_current_routes() -> None:
    assert [(item.route, item.runtime_method) for item in HEALTH_DIAGNOSTICS_CAPABILITIES] == [
        ("/health", "health"),
        ("/probe", "probe"),
        ("/turn/current", "turn_current"),
    ]


def test_health_diagnostics_service_probe_preserves_diagnostic_contract(tmp_path: Path) -> None:
    class ProbeRuntime:
        def __init__(self) -> None:
            self._sessions = {"old": object()}

        def _payload_text(self, payload: dict[str, object]) -> str:
            return str(payload.get("text") or "")

        async def _cleanup_idle_sessions(self) -> dict[str, int]:
            self._sessions.clear()
            return {"cleaned_sessions": 1}

    result = asyncio.run(
        HealthDiagnosticsService.probe(
            ProbeRuntime(),
            {"text": "hello"},
            bridge_version="service-probe",
            deps=object(),
        )
    )

    assert result == {
        "ok": True,
        "bridge": "xinyu_core_bridge",
        "version": "service-probe",
        "probe": "diagnostic_no_memory",
        "accepted": True,
        "reply": "probe_ok",
        "received_text_chars": 5,
        "memory_changed": False,
        "session_created": False,
        "sessions": 0,
        "cleaned_sessions": 1,
        "notes": ["no_agent_turn", "no_memory_write", "no_session_created"],
    }


def test_health_diagnostics_service_turn_current_preserves_operator_shape() -> None:
    runtime = SimpleNamespace()

    result = asyncio.run(
        HealthDiagnosticsService.turn_current(
            runtime,
            {"ignored": True},
            current_turn_snapshot_func=lambda received_runtime: {
                "current_turn": {"turn_id": "t1", "state": "running"},
                "presence": {
                    "current_turn_state": "running",
                    "current_turn_age_seconds": 5,
                    "stale_running": False,
                },
                "route": {
                    "last_stage": "model_inject_started",
                    "last_route": "slow_live",
                    "last_status": "running",
                },
            },
        )
    )

    assert result == {
        "ok": True,
        "current_turn": {"turn_id": "t1", "state": "running"},
        "route": {
            "last_stage": "model_inject_started",
            "last_route": "slow_live",
            "last_status": "running",
        },
        "operator": {
            "current_turn_state": "running",
            "current_turn_age_seconds": 5,
            "route_stage": "model_inject_started",
            "route": "slow_live",
            "route_status": "running",
            "stale_running": False,
            "stale_age_seconds": 0,
            "last_timeout_stage": "",
            "last_timeout_reason": "",
        },
    }


def test_health_diagnostics_service_uses_injected_dependencies(tmp_path: Path) -> None:
    calls: list[str] = []
    service = build_health_diagnostics_service(
        HealthDiagnosticsDeps(
            read_code_awareness_summary_func=lambda root: calls.append("code") or {"available": True},
            read_runtime_presence_summary_func=lambda root: calls.append("presence")
            or {"current_turn_state": "idle"},
            read_turn_route_summary_func=lambda root: calls.append("route")
            or {"last_stage": "none", "last_status": "ok"},
            read_recent_action_digest_snapshot_func=lambda root, *, limit: calls.append(f"digest:{limit}")
            or {"recent": []},
            autonomous_maintenance_health_func=lambda runtime: calls.append("autonomous") or {"enabled": False},
            metabolism_health_func=lambda runtime: calls.append("metabolism") or {"task_running": False},
            operator_health_func=lambda **kwargs: calls.append("operator") or {"current_turn_state": "idle"},
        )
    )

    result = service.health_snapshot(
        _runtime(tmp_path),
        bridge_version="service-version",
        source_digest="service-source",
        runtime_source_digest="service-runtime",
    )

    assert result["version"] == "service-version"
    assert result["code_awareness"]["running_bridge_digest"] == "service-source"
    assert result["operator"]["current_turn_state"] == "idle"
    assert "service_health" not in result
    assert calls == ["code", "presence", "route", "autonomous", "operator", "metabolism", "digest:3"]


def test_health_diagnostics_service_consumes_injected_service_health_providers(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    contract = health_diagnostics_service_health_contract()
    provider_calls: list[tuple[str, object]] = []

    def provider(service_id: str):
        def health(bound_runtime: object) -> dict[str, object]:
            provider_calls.append((service_id, bound_runtime))
            return {
                "ok": True,
                "ready": True,
                "status": "ok",
                "mode": "in_process",
                "notes": [f"{service_id}:ok"],
            }

        return health

    service = build_health_diagnostics_service(
        HealthDiagnosticsDeps(
            read_code_awareness_summary_func=lambda root: {"available": False},
            read_runtime_presence_summary_func=lambda root: {"current_turn_state": "idle"},
            read_turn_route_summary_func=lambda root: {"last_stage": "none", "last_status": "ok"},
            read_recent_action_digest_snapshot_func=lambda root, *, limit: {"recent": []},
            autonomous_maintenance_health_func=lambda runtime: {"enabled": False},
            metabolism_health_func=lambda runtime: {"task_running": False},
            operator_health_func=lambda **kwargs: {"current_turn_state": "idle"},
            service_health_providers_func=lambda runtime: tuple(
                HealthDiagnosticsServiceHealthProvider(service_id, provider(service_id))
                for service_id in contract.required_provider_service_ids
            ),
        )
    )

    result = service.health_snapshot(
        runtime,
        bridge_version="service-version",
        source_digest="service-source",
        runtime_source_digest="service-runtime",
    )

    service_health = result["service_health"]
    assert service_health["ok"] is True
    assert service_health["service_health_status"] == "ok"
    assert service_health["service_count"] == len(contract.required_provider_service_ids)
    assert service_health["degraded_count"] == 0
    assert set(service_health["services"]) == set(contract.required_provider_service_ids)
    assert provider_calls == [(service_id, runtime) for service_id in contract.required_provider_service_ids]


def test_health_diagnostics_service_lifecycle_readiness_and_fallback(tmp_path: Path) -> None:
    service = build_health_diagnostics_service(
        HealthDiagnosticsDeps(
            read_code_awareness_summary_func=lambda root: {"available": False},
            read_runtime_presence_summary_func=lambda root: {"current_turn_state": "idle"},
            read_turn_route_summary_func=lambda root: {"last_stage": "none", "last_status": "ok"},
            read_recent_action_digest_snapshot_func=lambda root, *, limit: {"recent": []},
            autonomous_maintenance_health_func=lambda runtime: {"enabled": False},
            metabolism_health_func=lambda runtime: {"task_running": False},
            operator_health_func=lambda **kwargs: {"current_turn_state": "idle"},
        )
    )

    initial = service.readiness()
    assert initial.service_id == "health_diagnostics"
    assert initial.mode == "in_process"
    assert initial.started is False
    assert initial.ready is False
    assert initial.state_owner == HEALTH_DIAGNOSTICS_STATE_OWNER
    assert initial.fallback_adapter == HEALTH_DIAGNOSTICS_FALLBACK_ADAPTER
    assert initial.rollback == HEALTH_DIAGNOSTICS_ROLLBACK

    started = service.start()
    assert started.started is True
    assert started.ready is True

    fallback_snapshot = service.fallback_adapter()(
        _runtime(tmp_path),
        bridge_version="fallback-version",
        source_digest="fallback-source",
        runtime_source_digest="fallback-runtime",
    )
    assert fallback_snapshot["version"] == "fallback-version"
    assert fallback_snapshot["source_digest"] == "fallback-source"

    stopped = service.stop()
    assert stopped.started is False
    assert stopped.ready is False


def test_health_diagnostics_preflight_ready_for_process_split() -> None:
    contract = health_diagnostics_preflight_contract()

    assert contract.service_id == "health_diagnostics"
    assert contract.ready is True
    assert contract.required_gates == HEALTH_DIAGNOSTICS_S3_PREFLIGHT_GATES
    assert contract.satisfied_gates == HEALTH_DIAGNOSTICS_S3_SATISFIED_GATES
    assert contract.missing_gates == ()
    assert contract.injected_dependencies == HEALTH_DIAGNOSTICS_INJECTED_DEPENDENCIES
    assert contract.runtime_internal_fields == HEALTH_DIAGNOSTICS_RUNTIME_INTERNAL_FIELDS
    assert "_sessions" in contract.runtime_internal_fields
    assert "_autonomous_task" in contract.runtime_internal_fields
    assert "_payload_text" in contract.runtime_internal_fields
    assert "health_snapshot" not in contract.runtime_internal_fields
    assert "self_choice_store.health_snapshot" in contract.runtime_internal_fields
    assert "process_split_ready_uses_provider_registry_rollback" in contract.notes
    assert health_diagnostics_preflight_contract(contract.required_gates).ready is True


def test_health_diagnostics_service_health_aggregation_contract() -> None:
    runtime = object()
    calls: list[str] = []

    def healthy(bound_runtime: object) -> dict[str, object]:
        assert bound_runtime is runtime
        calls.append("healthy")
        return {
            "ok": True,
            "ready": True,
            "status": "ready",
            "mode": "in_process",
            "details": {"latency_ms": 1},
            "notes": ["healthy"],
        }

    def broken(bound_runtime: object) -> dict[str, object]:
        assert bound_runtime is runtime
        calls.append("broken")
        raise RuntimeError("private details must not leak")

    contract = health_diagnostics_service_health_contract()
    summary = aggregate_service_health(
        (
            HealthDiagnosticsServiceHealthProvider("healthy_service", healthy),
            HealthDiagnosticsServiceHealthProvider("broken_service", broken),
        ),
        runtime,
        required_service_ids=("healthy_service", "broken_service"),
    )

    assert contract.provider_fields == (
        "service_id",
        "mode",
        "started",
        "ready",
        "state_owner",
        "fallback_adapter",
        "rollback",
        "notes",
    )
    assert contract.health_result_fields == (
        "service_id",
        "available",
        "ok",
        "status",
        "payload",
        "error_type",
        "error_message",
        "notes",
    )
    assert contract.summary_fields == (
        "ok",
        "service_health_status",
        "service_count",
        "degraded_count",
        "services",
    )
    assert "provider_exception" in contract.failure_notes
    assert "aggregation_does_not_set_process_split_ready" in contract.semantics
    assert calls == ["healthy", "broken"]
    assert summary["ok"] is False
    assert summary["service_health_status"] == "unknown"
    assert summary["service_count"] == 2
    assert summary["degraded_count"] == 1
    assert summary["services"]["healthy_service"] == {
        "service_id": "healthy_service",
        "available": True,
        "ok": True,
        "status": "ok",
        "payload": {"ready": True, "mode": "in_process", "details": {"latency_ms": 1}},
        "error_type": "",
        "error_message": "",
        "notes": ("healthy",),
    }
    assert summary["services"]["broken_service"] == {
        "service_id": "broken_service",
        "available": True,
        "ok": False,
        "status": "unknown",
        "payload": {},
        "error_type": "RuntimeError",
        "error_message": "",
        "notes": ("provider_exception",),
    }
    assert "private details must not leak" not in str(summary)
