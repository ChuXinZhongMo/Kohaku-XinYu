from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from xinyu_bridge_health_diagnostics_service import (
    HEALTH_DIAGNOSTICS_FALLBACK_ADAPTER,
    HEALTH_DIAGNOSTICS_INJECTED_DEPENDENCIES,
    HEALTH_DIAGNOSTICS_ROLLBACK,
    HEALTH_DIAGNOSTICS_RUNTIME_INTERNAL_FIELDS,
    HEALTH_DIAGNOSTICS_S3_PREFLIGHT_GATES,
    HEALTH_DIAGNOSTICS_S3_SATISFIED_GATES,
    HEALTH_DIAGNOSTICS_STATE_OWNER,
    HealthDiagnosticsDeps,
    build_health_diagnostics_service,
    health_diagnostics_preflight_contract,
    health_diagnostics_service_health_aggregation_contract,
)
from xinyu_serviceization_contracts import process_split_ready_contracts, service_contract_by_id
from xinyu_serviceization_readiness import (
    SERVICE_PILOT_PREFLIGHT_REQUIRED_GATES,
    assess_service_pilot_preflight,
    assess_service_split_readiness,
)


SERVICE_HEALTH_AGGREGATION_GATE = "service_health_aggregation_contract"


class _SelfChoiceStore:
    def health_snapshot(self) -> dict[str, object]:
        return {"available": True}


def _runtime(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        xinyu_dir=root,
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
        _v1_health=lambda: {"enabled": False},
        self_choice_store=_SelfChoiceStore(),
        _closed=False,
    )


def _deps(calls: list[tuple[str, Any]] | None = None) -> HealthDiagnosticsDeps:
    call_log = [] if calls is None else calls

    return HealthDiagnosticsDeps(
        read_code_awareness_summary_func=lambda root: call_log.append(("code", root)) or {"available": True},
        read_runtime_presence_summary_func=lambda root: call_log.append(("presence", root))
        or {
            "current_turn_state": "idle",
            "current_turn_age_seconds": 0,
            "stale_running": False,
        },
        read_turn_route_summary_func=lambda root: call_log.append(("route", root))
        or {
            "last_stage": "none",
            "last_route": "none",
            "last_status": "ok",
        },
        read_recent_action_digest_snapshot_func=lambda root, *, limit: call_log.append(("digest", (root, limit)))
        or {"recent": []},
        autonomous_maintenance_health_func=lambda runtime: call_log.append(("autonomous", runtime))
        or {"enabled": False},
        metabolism_health_func=lambda runtime: call_log.append(("metabolism", runtime)) or {"task_running": False},
        operator_health_func=lambda **kwargs: call_log.append(("operator", kwargs)) or {"current_turn_state": "idle"},
    )


def test_health_diagnostics_dependencies_are_injected_and_frozen(tmp_path: Path) -> None:
    calls: list[tuple[str, Any]] = []
    deps = _deps(calls)
    service = build_health_diagnostics_service(deps)

    with pytest.raises(FrozenInstanceError):
        deps.read_code_awareness_summary_func = lambda root: {}  # type: ignore[misc]

    assert HEALTH_DIAGNOSTICS_INJECTED_DEPENDENCIES == (
        "read_code_awareness_summary_func",
        "read_runtime_presence_summary_func",
        "read_turn_route_summary_func",
        "read_recent_action_digest_snapshot_func",
        "autonomous_maintenance_health_func",
        "metabolism_health_func",
        "operator_health_func",
        "service_health_providers_func",
    )
    assert tuple(field.name for field in fields(HealthDiagnosticsDeps)) == HEALTH_DIAGNOSTICS_INJECTED_DEPENDENCIES

    result = service.health_snapshot(
        _runtime(tmp_path),
        bridge_version="health-preflight",
        source_digest="bridge-digest",
        runtime_source_digest="runtime-digest",
    )

    assert result["version"] == "health-preflight"
    assert result["code_awareness"]["running_bridge_digest"] == "bridge-digest"
    assert [name for name, _ in calls] == [
        "code",
        "presence",
        "route",
        "autonomous",
        "operator",
        "metabolism",
        "digest",
    ]
    assert calls[0] == ("code", tmp_path)
    assert calls[-1] == ("digest", (tmp_path, 3))
    assert not (tmp_path / "runtime").exists()
    assert not (tmp_path / "memory").exists()


def test_health_diagnostics_fallback_stays_in_process(tmp_path: Path) -> None:
    contract = service_contract_by_id("health_diagnostics")
    service = build_health_diagnostics_service(_deps())

    initial = service.readiness()
    assert initial.service_id == "health_diagnostics"
    assert initial.mode == "in_process"
    assert initial.started is False
    assert initial.ready is False
    assert initial.api_routes == contract.api_routes
    assert initial.runtime_facade_methods == contract.runtime_facade_methods
    assert initial.process_split_candidate is True
    assert initial.process_split_ready is True
    assert initial.process_split_gate == contract.process_split_gate
    assert initial.state_owner == HEALTH_DIAGNOSTICS_STATE_OWNER
    assert initial.fallback_adapter == HEALTH_DIAGNOSTICS_FALLBACK_ADAPTER
    assert initial.rollback == HEALTH_DIAGNOSTICS_ROLLBACK
    assert "no_background_resources" in initial.notes

    started = service.start()
    assert started.mode == "in_process"
    assert started.started is True
    assert started.ready is True

    fallback = service.fallback_adapter()
    assert fallback.__self__ is service  # type: ignore[attr-defined]
    assert fallback.__name__ == "health_snapshot"

    snapshot = fallback(
        _runtime(tmp_path),
        bridge_version="fallback-version",
        source_digest="fallback-source",
        runtime_source_digest="fallback-runtime",
    )
    assert snapshot["version"] == "fallback-version"
    assert snapshot["source_digest"] == "fallback-source"


def test_health_diagnostics_is_process_split_ready() -> None:
    contract = service_contract_by_id("health_diagnostics")
    health_preflight = health_diagnostics_preflight_contract()
    split_readiness = assess_service_split_readiness(contract)
    pilot_preflight = assess_service_pilot_preflight(contract)

    assert contract.process_split_candidate is True
    assert contract.process_split_ready is True
    assert health_preflight.service_id == "health_diagnostics"
    assert health_preflight.ready is True
    assert split_readiness.ready is True
    assert pilot_preflight.preflight_ready is True
    assert pilot_preflight.process_split_ready is True
    assert "health_diagnostics" in {item.service_id for item in process_split_ready_contracts()}
    assert pilot_preflight.split_blockers == ()


def test_health_diagnostics_rollback_smoke_is_declared_and_in_process() -> None:
    service_contract = service_contract_by_id("health_diagnostics")
    health_preflight = health_diagnostics_preflight_contract()
    aggregation_contract = health_diagnostics_service_health_aggregation_contract()
    smoke_path = "tests/smoke/bridge/health_diagnostics_rollback_smoke.py"
    registry_smoke_path = "tests/smoke/bridge/health_diagnostics_provider_registry_smoke.py"
    registry_service_smoke_path = "tests/smoke/bridge/health_diagnostics_provider_registry_service_smoke.py"
    root = Path(__file__).resolve().parents[1]

    assert health_preflight.rollback == HEALTH_DIAGNOSTICS_ROLLBACK
    assert health_preflight.ready is True
    assert health_preflight.missing_gates == ()
    assert "rollback" in aggregation_contract.provider_fields
    assert "does_not_call_runtime_health_snapshot" in aggregation_contract.semantics
    assert "does_not_read_runtime_internal_fields" in aggregation_contract.semantics
    assert smoke_path in service_contract.validation_tests
    assert registry_smoke_path in service_contract.validation_tests
    assert registry_service_smoke_path in service_contract.validation_tests
    assert (root / smoke_path).exists()
    assert (root / registry_smoke_path).exists()
    assert (root / registry_service_smoke_path).exists()


def test_health_diagnostics_preflight_satisfies_service_health_aggregation_gate() -> None:
    contract = service_contract_by_id("health_diagnostics")
    health_preflight = health_diagnostics_preflight_contract()
    pilot_preflight = assess_service_pilot_preflight(contract)
    required_gates = SERVICE_PILOT_PREFLIGHT_REQUIRED_GATES["health_diagnostics"]

    assert health_preflight.required_gates == HEALTH_DIAGNOSTICS_S3_PREFLIGHT_GATES
    assert health_preflight.satisfied_gates == HEALTH_DIAGNOSTICS_S3_SATISFIED_GATES
    assert health_preflight.runtime_internal_fields == HEALTH_DIAGNOSTICS_RUNTIME_INTERNAL_FIELDS
    assert health_preflight.injected_dependencies == HEALTH_DIAGNOSTICS_INJECTED_DEPENDENCIES
    assert "s3_health_aggregation_preflight_contract_only" in health_preflight.notes
    assert SERVICE_HEALTH_AGGREGATION_GATE in health_preflight.required_gates
    assert SERVICE_HEALTH_AGGREGATION_GATE in required_gates
    assert SERVICE_HEALTH_AGGREGATION_GATE in health_preflight.satisfied_gates
    assert SERVICE_HEALTH_AGGREGATION_GATE in pilot_preflight.satisfied_gates
    assert health_preflight.missing_gates == ()
    assert pilot_preflight.missing_gates == ()
    assert pilot_preflight.preflight_ready is True


def test_expected_service_health_aggregation_contract_shape() -> None:
    from xinyu_bridge_health_diagnostics_service import health_diagnostics_service_health_aggregation_contract

    contract = health_diagnostics_service_health_aggregation_contract()
    health_preflight_with_aggregation = health_diagnostics_preflight_contract(
        (*HEALTH_DIAGNOSTICS_S3_SATISFIED_GATES, SERVICE_HEALTH_AGGREGATION_GATE)
    )

    assert contract.service_id == "health_diagnostics"
    assert contract.gate == SERVICE_HEALTH_AGGREGATION_GATE
    assert contract.aggregate_field == "services"
    assert contract.aggregate_status_field == "service_health_status"
    assert contract.provider_method == "readiness"
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
    assert contract.required_provider_service_ids == (
        "chat_turn",
        "codex_execution",
        "desktop_event_stream",
        "desktop_surface",
        "diagnostic_reports",
        "external_action",
        "health_diagnostics",
        "learning_ingest",
        "life_metabolism",
        "memory_governance_reports",
        "proactive_delivery",
        "state_persistence",
    )
    assert contract.status_precedence == ("failed", "degraded", "unknown", "ok")
    assert contract.provider_failure_status == "unknown"
    assert "provider_exception_becomes_unknown_service_entry" in contract.semantics
    assert "does_not_call_runtime_health_snapshot" in contract.semantics
    assert "does_not_read_runtime_internal_fields" in contract.semantics
    assert SERVICE_HEALTH_AGGREGATION_GATE in health_preflight_with_aggregation.satisfied_gates
    assert health_preflight_with_aggregation.missing_gates == ()
