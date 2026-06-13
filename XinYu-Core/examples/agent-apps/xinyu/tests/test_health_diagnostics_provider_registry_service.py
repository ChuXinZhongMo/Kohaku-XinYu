from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from xinyu_bridge_health_diagnostics_service import aggregate_service_health
from xinyu_bridge_health_provider_registry import (
    HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_HTTP_MODE,
    HttpHealthDiagnosticsProviderRegistry,
)
from xinyu_bridge_health_provider_registry_service import (
    HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_MODE,
    HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_ROUTES,
    HealthDiagnosticsProviderRegistryService,
    health_provider_registry_service_transport,
)
from xinyu_bridge_health_service_providers import service_health_provider_ids
from xinyu_serviceization_contracts import service_boundary_contracts, service_contract_by_id


def test_health_provider_registry_service_readiness_is_dry_run_and_side_effect_free() -> None:
    readiness = HealthDiagnosticsProviderRegistryService().readiness()

    assert readiness.service_id == "health_diagnostics"
    assert readiness.mode == HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_MODE
    assert readiness.ready is True
    assert readiness.dry_run is True
    assert readiness.mutates_state is False
    assert readiness.routes == HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_ROUTES
    assert readiness.provider_ids == service_health_provider_ids()
    assert readiness.provider_count == len(service_health_provider_ids())
    assert set(readiness.provider_ids) == {contract.service_id for contract in service_boundary_contracts()}


def test_health_provider_registry_service_health_route_exposes_readiness_payload() -> None:
    health = HealthDiagnosticsProviderRegistryService().handle_request("GET", "/health")

    assert health["ok"] is True
    assert health["service_id"] == "health_diagnostics"
    assert health["mode"] == HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_MODE
    assert tuple(health["routes"]) == HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_ROUTES
    assert tuple(health["provider_ids"]) == service_health_provider_ids()
    assert health["mutates_state"] is False


def test_health_provider_registry_service_returns_dry_run_service_health() -> None:
    service = HealthDiagnosticsProviderRegistryService(
        service_payloads={"codex_execution": {"custom": "ok"}}
    )

    result = service.handle_request("GET", "/health/services/codex_execution")

    assert result["service_id"] == "codex_execution"
    assert result["ok"] is True
    assert result["ready"] is True
    assert result["status"] == "ok"
    assert result["payload"]["custom"] == "ok"
    assert result["payload"]["dry_run"] is True
    assert result["payload"]["provider_registry_service"] is True
    assert "runtime_state_not_written" in result["notes"]


def test_health_provider_registry_service_transport_connects_http_registry(tmp_path: Path) -> None:
    service = HealthDiagnosticsProviderRegistryService()
    registry = HttpHealthDiagnosticsProviderRegistry(
        endpoint="http://127.0.0.1:8791/",
        enabled=True,
        transport=health_provider_registry_service_transport(service),
    )
    runtime = SimpleNamespace(xinyu_dir=tmp_path, memory_root=tmp_path / "memory")
    readiness = registry.readiness(runtime)
    summary = aggregate_service_health(registry.providers(runtime), runtime)

    assert readiness.mode == HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_HTTP_MODE
    assert readiness.ready is True
    assert readiness.provider_count == len(service_health_provider_ids())
    assert summary["ok"] is True
    assert summary["service_count"] == len(service_health_provider_ids())
    assert set(summary["services"]) == set(service_health_provider_ids())
    assert summary["services"]["health_diagnostics"]["payload"]["source"] == (
        HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_SERVICE_MODE
    )
    assert not (tmp_path / "runtime").exists()
    assert not (tmp_path / "memory").exists()


def test_health_provider_registry_service_not_ready_requests_in_process_fallback() -> None:
    result = HealthDiagnosticsProviderRegistryService(ready=False).handle_request(
        "GET",
        "/health/services/health_diagnostics",
    )

    assert result["service_id"] == "health_diagnostics"
    assert result["ok"] is False
    assert result["ready"] is False
    assert result["status"] == "degraded"
    assert result["payload"]["fallback_registry"] == "in_process_provider_registry"
    assert result["http_status"] == 503


def test_health_provider_registry_service_rejects_unknown_or_invalid_routes() -> None:
    service = HealthDiagnosticsProviderRegistryService(provider_ids=("health_diagnostics",))

    assert service.handle_request("GET", "/missing")["http_status"] == 404
    assert service.handle_request("POST", "/health")["http_status"] == 405
    assert service.handle_request("GET", "/health/services/codex_execution")["http_status"] == 404


def test_health_provider_registry_service_declared_on_health_contract() -> None:
    contract = service_contract_by_id("health_diagnostics")

    assert contract.process_adapter_kind == "provider_registry"
    assert "xinyu_bridge_health_provider_registry_service.py" in contract.contract_modules
    assert "tests/test_health_diagnostics_provider_registry_service.py" in contract.validation_tests
    assert (
        "tests/smoke/bridge/health_diagnostics_provider_registry_service_smoke.py"
        in contract.validation_tests
    )
