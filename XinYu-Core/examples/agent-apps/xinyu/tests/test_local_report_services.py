from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_http_routes import post_route_requires_bridge_token
from xinyu_bridge_local_report_services import (
    DIAGNOSTIC_REPORTS_SERVICE_ID,
    LOCAL_REPORT_SERVICE_MODE_LOCAL,
    MEMORY_GOVERNANCE_REPORTS_SERVICE_ID,
    build_diagnostic_reports_service_handle,
    build_memory_governance_reports_service_handle,
    diagnostic_reports_service_config_from_env,
    diagnostic_reports_service_readiness,
    memory_governance_reports_service_config_from_env,
    memory_governance_reports_service_readiness,
)
from xinyu_serviceization_contracts import service_contract_by_id


def test_local_report_service_configs_are_local_only() -> None:
    diagnostic = diagnostic_reports_service_config_from_env({})
    memory = memory_governance_reports_service_config_from_env({})

    assert diagnostic.service_id == DIAGNOSTIC_REPORTS_SERVICE_ID
    assert diagnostic.mode == LOCAL_REPORT_SERVICE_MODE_LOCAL
    assert memory.service_id == MEMORY_GOVERNANCE_REPORTS_SERVICE_ID
    assert memory.mode == LOCAL_REPORT_SERVICE_MODE_LOCAL


def test_diagnostic_reports_service_lifecycle_readiness() -> None:
    handle = build_diagnostic_reports_service_handle()

    before = handle.readiness()
    started = handle.start()
    closed = handle.close()

    assert before.service_id == "diagnostic_reports"
    assert before.started is False
    assert before.ready is False
    assert started.started is True
    assert started.ready is True
    assert started.local_only is True
    assert started.process_split_candidate is False
    assert started.process_split_ready is False
    assert started.api_routes == ()
    assert started.runtime_facade_methods == ()
    assert started.local_route_control_plane is False
    assert started.control_plane_routes == ()
    assert started.token_required_routes == ()
    assert started.control_plane_requires_bridge_token is False
    assert started.missing_contract_modules == ()
    assert started.missing_validation_tests == ()
    assert closed.started is False
    assert closed.ready is False


def test_memory_governance_reports_service_lifecycle_readiness() -> None:
    handle = build_memory_governance_reports_service_handle()

    readiness = handle.start()
    contract = service_contract_by_id("memory_governance_reports")

    assert readiness.service_id == "memory_governance_reports"
    assert readiness.ready is True
    assert readiness.local_owner == contract.local_owner
    assert readiness.owner_layer == contract.owner_layer
    assert readiness.contract_module_count == len(contract.contract_modules)
    assert readiness.validation_test_count == len(contract.validation_tests)
    assert readiness.local_only is True
    assert readiness.process_split_candidate is False
    assert readiness.api_routes == contract.api_routes
    assert readiness.runtime_facade_methods == contract.runtime_facade_methods
    assert readiness.local_route_control_plane is True
    assert readiness.control_plane_routes == contract.api_routes
    assert readiness.token_required_routes == contract.api_routes
    assert readiness.control_plane_requires_bridge_token is True
    assert "local_route_control_plane" in readiness.notes
    assert "token_required_route_control_plane" in readiness.notes


def test_memory_governance_report_routes_remain_token_required() -> None:
    contract = service_contract_by_id("memory_governance_reports")

    assert contract.api_routes == (
        "/review/inbox/command",
        "/review/goldmark/mark_request",
    )
    assert all(post_route_requires_bridge_token(route) for route in contract.api_routes)


def test_local_report_service_readiness_reports_missing_contract_files(tmp_path) -> None:
    handle = build_diagnostic_reports_service_handle(repo_root=tmp_path)

    readiness = handle.start()

    assert readiness.ready is False
    assert "xinyu_module_ecology_audit.py" in readiness.missing_contract_modules
    assert "tests/test_module_ecology_audit.py" in readiness.missing_validation_tests


def test_local_report_service_pre_start_probe_does_not_cache_inventory(tmp_path) -> None:
    handle = build_diagnostic_reports_service_handle(repo_root=tmp_path)

    before = handle.readiness()
    (tmp_path / "tests").mkdir()
    (tmp_path / "xinyu_module_ecology_audit.py").write_text("", encoding="utf-8")
    (tmp_path / "tests" / "test_module_ecology_audit.py").write_text("", encoding="utf-8")
    started = handle.start()

    assert "xinyu_module_ecology_audit.py" in before.missing_contract_modules
    assert "tests/test_module_ecology_audit.py" in before.missing_validation_tests
    assert "xinyu_module_ecology_audit.py" not in started.missing_contract_modules
    assert "tests/test_module_ecology_audit.py" not in started.missing_validation_tests


def test_local_report_service_readiness_helpers_use_runtime_handles() -> None:
    diagnostic = build_diagnostic_reports_service_handle()
    memory = build_memory_governance_reports_service_handle()
    runtime = SimpleNamespace(
        _diagnostic_reports_service=diagnostic,
        _memory_governance_reports_service=memory,
    )

    diagnostic.start()
    memory.start()

    assert diagnostic_reports_service_readiness(runtime).ready is True
    assert memory_governance_reports_service_readiness(runtime).ready is True
