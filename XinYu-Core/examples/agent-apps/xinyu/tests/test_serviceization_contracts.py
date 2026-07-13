from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

from xinyu_bridge_codex_execution_service import (
    CODEX_EXECUTION_SERVICE_CONFIG_BACKEND_ENV,
    CODEX_EXECUTION_SERVICE_CONFIG_CANCEL_TIMEOUT_ENV,
    CODEX_EXECUTION_SERVICE_CONFIG_ENDPOINT_ENV,
    CODEX_EXECUTION_SERVICE_CONFIG_FALLBACK_ENV,
    CODEX_EXECUTION_SERVICE_CONFIG_HEALTH_TIMEOUT_ENV,
    CODEX_EXECUTION_SERVICE_CONFIG_SUBMIT_TIMEOUT_ENV,
    CODEX_EXECUTION_SERVICE_CONFIG_WORKER_ENABLED_ENV,
    CODEX_EXECUTION_SERVICE_CONFIG_WORKER_HEALTHY_ENV,
)
from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_EVENT_STREAM_EXTERNALIZATION_SCOPE,
    DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY,
    DESKTOP_EVENT_STREAM_RUNTIME_ATTR,
    desktop_event_stream_readiness,
)
from xinyu_bridge_desktop_surface_service import (
    DESKTOP_SURFACE_SERVICE_CONFIG_BACKEND_ENV,
    DESKTOP_SURFACE_SERVICE_CONFIG_ENDPOINT_ENV,
    DESKTOP_SURFACE_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
)
from xinyu_bridge_external_action_service import (
    EXTERNAL_ACTION_SERVICE_CONFIG_BACKEND_ENV,
    EXTERNAL_ACTION_SERVICE_CONFIG_DRY_RUN_ENV,
    EXTERNAL_ACTION_SERVICE_CONFIG_ENDPOINT_ENV,
)
from xinyu_bridge_http_dispatch_table import GET_ROUTE_DISPATCH, POST_ROUTE_DISPATCH
from xinyu_bridge_http_routes import (
    TOKEN_REQUIRED_POST_ROUTES,
    is_known_get_route,
    is_known_post_route,
    post_route_requires_bridge_token,
)
from xinyu_bridge_proactive_delivery_service import (
    PROACTIVE_DELIVERY_SERVICE_CONFIG_BACKEND_ENV,
    PROACTIVE_DELIVERY_SERVICE_CONFIG_ENDPOINT_ENV,
    PROACTIVE_DELIVERY_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
)
from xinyu_bridge_health_service_providers import service_health_provider_ids
from xinyu_runtime_security import runtime_source_paths
from xinyu_serviceization_contracts import (
    PROTECTED_PROCESS_SPLIT_MODULES,
    process_split_candidates,
    process_split_ready_contracts,
    service_boundary_contracts,
    service_contract_by_id,
    validate_service_boundary_contracts,
)


ROOT = Path(__file__).resolve().parents[1]
SERVICEIZATION_CONTRACT_COUNT = 12
DISPATCH_TABLE_SPECIAL_ROUTES = frozenset(
    {
        "/health",
        "/life/metabolism/tickets",
    }
)


def _route_known(route: str) -> bool:
    if route == "/life/metabolism/tickets":
        return is_known_get_route(route)
    return is_known_get_route(route) or is_known_post_route(route)


def _contract_route_owners() -> dict[str, set[str]]:
    route_owners: dict[str, set[str]] = {}
    for contract in service_boundary_contracts():
        for route in contract.api_routes:
            route_owners.setdefault(route, set()).add(contract.service_id)
    return route_owners


def test_serviceization_contracts_reference_existing_modules() -> None:
    assert validate_service_boundary_contracts(ROOT) == ()


def test_serviceization_contract_count_and_health_provider_count_remain_12() -> None:
    assert len(service_boundary_contracts()) == SERVICEIZATION_CONTRACT_COUNT
    assert len(service_health_provider_ids()) == SERVICEIZATION_CONTRACT_COUNT


def test_runtime_service_handle_tests_are_declared_in_service_contracts() -> None:
    service_test_overrides = {
        "diagnostic_reports": "tests/test_local_report_services.py",
        "memory_governance_reports": "tests/test_local_report_services.py",
    }

    for contract in service_boundary_contracts():
        expected = service_test_overrides.get(
            contract.service_id,
            f"tests/test_{contract.service_id}_service.py",
        )
        if not (ROOT / expected).exists():
            continue
        assert expected in contract.validation_tests, contract.service_id


def test_serviceization_contracts_cover_runtime_digest() -> None:
    digest_paths = tuple(runtime_source_paths(ROOT))
    missing_paths = tuple(path for path in digest_paths if not path.exists())
    missing_count = len(missing_paths)
    digest_names = {path.name for path in digest_paths}

    assert missing_count == 0
    assert missing_paths == ()
    assert "xinyu_serviceization_contracts.py" in digest_names


def test_protected_process_split_modules_exist() -> None:
    for protected_module in PROTECTED_PROCESS_SPLIT_MODULES:
        assert (ROOT / protected_module).exists()


def test_serviceization_contract_routes_are_current_http_contracts() -> None:
    for contract in service_boundary_contracts():
        for route in contract.api_routes:
            assert _route_known(route), f"{contract.service_id}: unknown route {route}"


def test_serviceization_contracts_cover_http_dispatch_table_routes() -> None:
    dispatch_routes = set(GET_ROUTE_DISPATCH) | set(POST_ROUTE_DISPATCH)
    contract_routes = set(_contract_route_owners())

    assert sorted(dispatch_routes - contract_routes) == []
    assert sorted(contract_routes - dispatch_routes - DISPATCH_TABLE_SPECIAL_ROUTES) == []


def test_serviceization_contracts_pin_control_plane_route_owners() -> None:
    route_owners = _contract_route_owners()

    expected_route_owners = {
        "/internal/message/ack": {"chat_turn"},
        "/internal/message/drop": {"chat_turn"},
        "/turn/cancel": {"chat_turn"},
        "/turn/retry-lightweight": {"chat_turn"},
        "/turn/skip-sidecar": {"chat_turn"},
        "/turn/continue": {"chat_turn"},
        "/turn/status-message": {"chat_turn"},
        "/sticker/import": {"learning_ingest"},
        "/review/goldmark/mark_request": {"memory_governance_reports"},
    }
    for route, owners in expected_route_owners.items():
        assert route_owners[route] == owners


def test_token_required_post_routes_have_unique_service_owners() -> None:
    route_owners = _contract_route_owners()
    expected_route_owners = {
        "/codex/execute": {"codex_execution"},
        "/package/install": {"external_action"},
        "/qq/outbox/claim": {"proactive_delivery"},
        "/qq/outbox/ack": {"proactive_delivery"},
        "/internal/message/ack": {"chat_turn"},
        "/internal/message/drop": {"chat_turn"},
        "/review/inbox/command": {"memory_governance_reports"},
        "/review/goldmark/mark_request": {"memory_governance_reports"},
        "/sticker/import": {"learning_ingest"},
        "/external/call": {"external_action"},
        "/external/plugins/config": {"external_action"},
        "/external/plugins/install": {"external_action"},
        "/desktop/private-ecosystem/pause": {"external_action"},
        "/desktop/private-ecosystem/grant": {"external_action"},
        "/desktop/private-ecosystem/tick": {"external_action"},
        "/desktop/private-browser/action": {"external_action"},
        "/desktop/private-desktop/observe": {"external_action"},
        "/desktop/private-desktop/start": {"external_action"},
        "/desktop/private-desktop/stop": {"external_action"},
    }

    assert TOKEN_REQUIRED_POST_ROUTES == frozenset(expected_route_owners)
    for route, owners in expected_route_owners.items():
        assert route_owners[route] == owners


def test_dynamic_life_ticket_action_routes_are_owned_by_local_life_metabolism() -> None:
    life = service_contract_by_id("life_metabolism")

    for action in ("approve", "reject", "cancel"):
        route = f"/life/metabolism/tickets/ticket-1/{action}"
        assert is_known_post_route(route)
        assert post_route_requires_bridge_token(route)

    assert "/life/metabolism/tickets" in life.api_routes
    assert life.process_split_candidate is False
    assert life.process_split_ready is False


def test_health_diagnostics_and_codex_execution_are_marked_process_split_ready() -> None:
    assert {contract.service_id for contract in process_split_candidates()} == {
        "proactive_delivery",
        "desktop_surface",
        "desktop_event_stream",
        "codex_execution",
        "external_action",
        "health_diagnostics",
    }
    assert {contract.service_id for contract in process_split_ready_contracts()} == {
        "health_diagnostics",
        "codex_execution",
        "external_action",
        "desktop_event_stream",
        "proactive_delivery",
        "desktop_surface",
    }


def test_split_ready_service_adapter_kinds_are_explicit() -> None:
    expected_adapter_kinds = {
        "codex_execution": "worker_client",
        "desktop_event_stream": "ws_contract_only",
        "desktop_surface": "route_backend",
        "external_action": "execution_backend",
        "health_diagnostics": "provider_registry",
        "proactive_delivery": "route_backend",
    }
    allowed_adapter_kinds = {
        "execution_backend",
        "provider_registry",
        "route_backend",
        "worker_client",
        "ws_contract_only",
    }

    assert {
        contract.service_id: contract.process_adapter_kind
        for contract in process_split_ready_contracts()
    } == expected_adapter_kinds
    assert set(expected_adapter_kinds.values()).issubset(allowed_adapter_kinds)


def test_split_ready_process_harnesses_are_declared_and_dry_run_safe() -> None:
    worker_harnesses = {
        "codex_execution": (
            "worker_client",
            "xinyu_bridge_codex_execution_worker_service.py",
            "tests/test_codex_execution_worker_service.py",
            "tests/smoke/codex/codex_execution_worker_service_smoke.py",
            "xinyu_bridge_codex_execution_worker_service",
            "CodexExecutionWorkerService",
            {"dry_run": True, "executes_runtime": False},
        ),
        "desktop_surface": (
            "route_backend",
            "xinyu_bridge_desktop_surface_worker_service.py",
            "tests/test_desktop_surface_worker_service.py",
            "tests/smoke/bridge/desktop_surface_worker_service_smoke.py",
            "xinyu_bridge_desktop_surface_worker_service",
            "DesktopSurfaceWorkerService",
            {"dry_run": True, "mutates_state": False, "owns_websocket_lifecycle": False},
        ),
        "external_action": (
            "execution_backend",
            "xinyu_bridge_external_action_worker_service.py",
            "tests/test_external_action_worker_service.py",
            "tests/smoke/bridge/external_action_worker_service_smoke.py",
            "xinyu_bridge_external_action_worker_service",
            "ExternalActionWorkerService",
            {"dry_run": True, "executes_runtime": False},
        ),
        "proactive_delivery": (
            "route_backend",
            "xinyu_bridge_proactive_delivery_worker_service.py",
            "tests/test_proactive_delivery_worker_service.py",
            "tests/smoke/bridge/proactive_delivery_worker_service_smoke.py",
            "xinyu_bridge_proactive_delivery_worker_service",
            "ProactiveDeliveryWorkerService",
            {"dry_run": True, "mutates_state": False, "touches_qq_gateway": False},
        ),
    }
    split_ready = {contract.service_id: contract for contract in process_split_ready_contracts()}

    assert set(worker_harnesses) == {
        service_id
        for service_id, contract in split_ready.items()
        if contract.process_adapter_kind in {"execution_backend", "route_backend", "worker_client"}
    }
    for service_id, spec in worker_harnesses.items():
        (
            adapter_kind,
            module_path,
            test_path,
            smoke_path,
            module_name,
            service_class_name,
            readiness_fields,
        ) = spec
        contract = service_contract_by_id(service_id)
        module = importlib.import_module(module_name)
        readiness = getattr(module, service_class_name)().readiness()

        assert contract.process_adapter_kind == adapter_kind
        assert module_path in contract.contract_modules
        assert test_path in contract.validation_tests
        assert smoke_path in contract.validation_tests
        assert (ROOT / module_path).exists()
        assert (ROOT / test_path).exists()
        assert (ROOT / smoke_path).exists()
        assert readiness.service_id == service_id
        assert readiness.ready is True
        assert "/health" in readiness.routes
        assert readiness.rollback
        for field, expected in readiness_fields.items():
            assert getattr(readiness, field) is expected


def test_split_ready_provider_registry_and_ws_contract_only_are_not_worker_services() -> None:
    health = service_contract_by_id("health_diagnostics")
    stream = service_contract_by_id("desktop_event_stream")

    assert health.process_adapter_kind == "provider_registry"
    assert "xinyu_bridge_health_provider_registry.py" in health.contract_modules
    assert "xinyu_bridge_health_provider_registry_service.py" in health.contract_modules
    assert "tests/test_health_diagnostics_preflight_contract.py" in health.validation_tests
    assert "tests/test_health_diagnostics_provider_registry_service.py" in health.validation_tests
    assert "tests/smoke/bridge/health_diagnostics_provider_registry_smoke.py" in health.validation_tests
    assert "tests/smoke/bridge/health_diagnostics_provider_registry_service_smoke.py" in health.validation_tests
    assert not any("worker_service" in module for module in health.contract_modules)

    assert stream.process_adapter_kind == "ws_contract_only"
    assert "xinyu_desktop_ws.py" in stream.contract_modules
    assert "tests/test_desktop_event_stream_contract.py" in stream.validation_tests
    assert not any("worker_service" in module for module in stream.contract_modules)


def test_serviceization_adapter_env_example_documents_current_switches() -> None:
    example = (ROOT / "xinyu.local.env.example").read_text(encoding="utf-8")
    expected_env_names = {
        CODEX_EXECUTION_SERVICE_CONFIG_BACKEND_ENV,
        CODEX_EXECUTION_SERVICE_CONFIG_ENDPOINT_ENV,
        CODEX_EXECUTION_SERVICE_CONFIG_WORKER_ENABLED_ENV,
        CODEX_EXECUTION_SERVICE_CONFIG_WORKER_HEALTHY_ENV,
        CODEX_EXECUTION_SERVICE_CONFIG_FALLBACK_ENV,
        CODEX_EXECUTION_SERVICE_CONFIG_HEALTH_TIMEOUT_ENV,
        CODEX_EXECUTION_SERVICE_CONFIG_SUBMIT_TIMEOUT_ENV,
        CODEX_EXECUTION_SERVICE_CONFIG_CANCEL_TIMEOUT_ENV,
        EXTERNAL_ACTION_SERVICE_CONFIG_BACKEND_ENV,
        EXTERNAL_ACTION_SERVICE_CONFIG_DRY_RUN_ENV,
        EXTERNAL_ACTION_SERVICE_CONFIG_ENDPOINT_ENV,
        PROACTIVE_DELIVERY_SERVICE_CONFIG_BACKEND_ENV,
        PROACTIVE_DELIVERY_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
        PROACTIVE_DELIVERY_SERVICE_CONFIG_ENDPOINT_ENV,
        DESKTOP_SURFACE_SERVICE_CONFIG_BACKEND_ENV,
        DESKTOP_SURFACE_SERVICE_CONFIG_ROUTE_BACKEND_ENV,
        DESKTOP_SURFACE_SERVICE_CONFIG_ENDPOINT_ENV,
    }

    for env_name in expected_env_names:
        assert f"{env_name}=" in example, env_name
    assert "XINYU_DESKTOP_EVENT_STREAM_BACKEND" not in example
    assert "Desktop websocket lifecycle remains app-owned" in example


def test_local_not_ready_service_set_remains_fixed() -> None:
    local_not_ready = {
        contract.service_id
        for contract in service_boundary_contracts()
        if not contract.process_split_ready
    }

    assert local_not_ready == {
        "chat_turn",
        "learning_ingest",
        "life_metabolism",
        "diagnostic_reports",
        "memory_governance_reports",
        "state_persistence",
    }
    for service_id in local_not_ready:
        contract = service_contract_by_id(service_id)
        assert contract.process_split_candidate is False
        assert contract.process_split_ready is False


def test_local_not_ready_service_readiness_exposes_not_ready_flags() -> None:
    class ChatService:
        def prepare_request(self) -> None:
            return None

        def start_turn_clock(self) -> None:
            return None

    learning_service = SimpleNamespace(
        ingest=lambda payload: payload,
        study=lambda payload: payload,
        observe=lambda payload: payload,
    )
    runtime = SimpleNamespace(
        chat=lambda payload: payload,
        chat_service=ChatService(),
        learning_service=learning_service,
        _metabolism_task=None,
    )
    service_specs = {
        "chat_turn": ("xinyu_bridge_chat_turn_service", "build_chat_turn_service_handle"),
        "learning_ingest": ("xinyu_bridge_learning_ingest_service", "build_learning_ingest_service_handle"),
        "life_metabolism": ("xinyu_bridge_life_metabolism_service", "build_life_metabolism_service_handle"),
        "diagnostic_reports": ("xinyu_bridge_local_report_services", "build_diagnostic_reports_service_handle"),
        "memory_governance_reports": (
            "xinyu_bridge_local_report_services",
            "build_memory_governance_reports_service_handle",
        ),
        "state_persistence": ("xinyu_bridge_state_persistence_service", "build_state_persistence_service_handle"),
    }

    assert set(service_specs) == {
        contract.service_id
        for contract in service_boundary_contracts()
        if not contract.process_split_ready
    }
    for service_id, (module_name, build_handle_name) in service_specs.items():
        module = importlib.import_module(module_name)
        readiness = getattr(module, build_handle_name)().start(runtime)

        assert readiness.service_id == service_id
        assert readiness.local_only is True
        assert readiness.process_split_candidate is False
        assert readiness.process_split_ready is False


def test_state_persistence_modules_do_not_overlap_split_ready_services() -> None:
    persistence = service_contract_by_id("state_persistence")
    split_ready_modules = {
        module
        for contract in process_split_ready_contracts()
        for module in contract.contract_modules
    }

    assert persistence.process_split_candidate is False
    assert persistence.process_split_ready is False
    assert sorted(set(persistence.contract_modules) & split_ready_modules) == []


def test_split_ready_services_declare_backend_and_rollback_smokes() -> None:
    expected_smokes = {
        "proactive_delivery": {
            "tests/smoke/bridge/proactive_delivery_route_backend_selection_smoke.py",
        },
        "desktop_surface": {
            "tests/smoke/bridge/desktop_surface_route_backend_selection_smoke.py",
            "tests/smoke/desktop/xinyu_desktop_rest_smoke.py",
        },
        "desktop_event_stream": {
            "tests/smoke/desktop/xinyu_desktop_rest_smoke.py",
        },
        "codex_execution": {
            "tests/smoke/codex/codex_execution_worker_rollback_smoke.py",
            "tests/smoke/codex/codex_execution_facade_payload_smoke.py",
            "tests/smoke/codex/codex_execution_service_lifecycle_smoke.py",
        },
        "external_action": {
            "tests/smoke/bridge/external_action_backend_rollback_smoke.py",
            "tests/smoke/bridge/external_action_execution_boundary_smoke.py",
            "tests/smoke/bridge/external_action_route_backend_selection_smoke.py",
        },
        "health_diagnostics": {
            "tests/smoke/bridge/health_diagnostics_rollback_smoke.py",
            "tests/smoke/bridge/health_diagnostics_provider_registry_smoke.py",
            "tests/smoke/bridge/health_diagnostics_provider_registry_service_smoke.py",
        },
    }

    assert set(expected_smokes) == {
        contract.service_id for contract in process_split_ready_contracts()
    }
    for service_id, smoke_paths in expected_smokes.items():
        contract = service_contract_by_id(service_id)
        for smoke_path in smoke_paths:
            assert smoke_path in contract.validation_tests, service_id
            assert (ROOT / smoke_path).exists(), smoke_path


def test_split_ready_backend_readiness_exposes_runtime_attr_and_contract_rollback() -> None:
    backend_specs = {
        "proactive_delivery": (
            "xinyu_bridge_proactive_delivery_route_backend",
            "proactive_delivery_route_backend_readiness",
            "PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR",
        ),
        "desktop_surface": (
            "xinyu_bridge_desktop_surface_route_backend",
            "desktop_surface_route_backend_readiness",
            "DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR",
        ),
        "codex_execution": (
            "xinyu_bridge_codex_execution_backend",
            "codex_execution_backend_readiness",
            "CODEX_EXECUTION_BACKEND_RUNTIME_ATTR",
        ),
        "external_action": (
            "xinyu_bridge_external_action_backend",
            "external_action_backend_readiness",
            "EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR",
        ),
        "health_diagnostics": (
            "xinyu_bridge_health_provider_registry",
            "health_diagnostics_provider_registry_readiness",
            "HEALTH_DIAGNOSTICS_PROVIDER_REGISTRY_RUNTIME_ATTR",
        ),
    }

    assert set(backend_specs).issubset(
        {contract.service_id for contract in process_split_ready_contracts()}
    )
    for service_id, (module_name, readiness_name, runtime_attr_name) in backend_specs.items():
        module = importlib.import_module(module_name)
        readiness = getattr(module, readiness_name)(SimpleNamespace())

        assert readiness.service_id == service_id
        assert readiness.runtime_attr == getattr(module, runtime_attr_name)
        assert readiness.runtime_attr.startswith("_")
        assert readiness.rollback
        assert readiness.contract_rollback
        assert readiness.rollback != readiness.contract_rollback


def test_split_ready_route_backend_service_readiness_exposes_config_switch_metadata() -> None:
    service_specs = {
        "proactive_delivery": (
            "xinyu_bridge_proactive_delivery_service",
            "build_proactive_delivery_service_handle",
            "backend_config_env",
            "PROACTIVE_DELIVERY_SERVICE_CONFIG_BACKEND_ENV",
            "route_backend_config_env",
            "PROACTIVE_DELIVERY_SERVICE_CONFIG_ROUTE_BACKEND_ENV",
            "route_backend_enabled",
            "route_backend_runtime_attr",
            "PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR",
        ),
        "desktop_surface": (
            "xinyu_bridge_desktop_surface_service",
            "build_desktop_surface_service_handle",
            "backend_config_env",
            "DESKTOP_SURFACE_SERVICE_CONFIG_BACKEND_ENV",
            "route_backend_config_env",
            "DESKTOP_SURFACE_SERVICE_CONFIG_ROUTE_BACKEND_ENV",
            "route_backend_enabled",
            "route_backend_runtime_attr",
            "DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR",
        ),
        "external_action": (
            "xinyu_bridge_external_action_service",
            "build_external_action_service_handle",
            "backend_config_env",
            "EXTERNAL_ACTION_SERVICE_CONFIG_BACKEND_ENV",
            "dry_run_config_env",
            "EXTERNAL_ACTION_SERVICE_CONFIG_DRY_RUN_ENV",
            "backend_enabled",
            "backend_runtime_attr",
            "EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR",
        ),
    }

    assert set(service_specs).issubset(
        {contract.service_id for contract in process_split_ready_contracts()}
    )
    for service_id, spec in service_specs.items():
        (
            module_name,
            build_handle_name,
            backend_env_field,
            backend_env_name,
            enabled_env_field,
            enabled_env_name,
            enabled_field,
            runtime_attr_field,
            runtime_attr_name,
        ) = spec
        module = importlib.import_module(module_name)
        runtime = SimpleNamespace(desktop_event_bus=None, desktop_ws_server=None)
        readiness = getattr(module, build_handle_name)().start(runtime)

        assert readiness.service_id == service_id
        assert getattr(readiness, backend_env_field) == getattr(module, backend_env_name)
        assert getattr(readiness, enabled_env_field) == getattr(module, enabled_env_name)
        assert getattr(readiness, enabled_field) is False
        assert getattr(readiness, runtime_attr_field) == getattr(module, runtime_attr_name)
        assert getattr(readiness, runtime_attr_field).startswith("_")


def test_split_ready_service_defaults_do_not_inject_external_backends() -> None:
    service_specs = {
        "codex_execution": (
            "xinyu_bridge_codex_execution_service",
            "build_codex_execution_service_handle",
            "CODEX_EXECUTION_BACKEND_RUNTIME_ATTR",
            "injected_runtime_backend",
        ),
        "proactive_delivery": (
            "xinyu_bridge_proactive_delivery_service",
            "build_proactive_delivery_service_handle",
            "PROACTIVE_DELIVERY_ROUTE_BACKEND_RUNTIME_ATTR",
            "route_backend_injected",
        ),
        "desktop_surface": (
            "xinyu_bridge_desktop_surface_service",
            "build_desktop_surface_service_handle",
            "DESKTOP_SURFACE_ROUTE_BACKEND_RUNTIME_ATTR",
            "route_backend_injected",
        ),
        "external_action": (
            "xinyu_bridge_external_action_service",
            "build_external_action_service_handle",
            "EXTERNAL_ACTION_BACKEND_RUNTIME_ATTR",
            "injected_runtime_backend",
        ),
    }

    assert set(service_specs).issubset(
        {contract.service_id for contract in process_split_ready_contracts()}
    )
    for service_id, (module_name, build_handle_name, runtime_attr_name, injected_field) in service_specs.items():
        module = importlib.import_module(module_name)
        runtime = SimpleNamespace(desktop_event_bus=None, desktop_ws_server=None)
        readiness = getattr(module, build_handle_name)().start(runtime)

        assert readiness.service_id == service_id
        assert getattr(readiness, injected_field) is False
        assert not hasattr(runtime, getattr(module, runtime_attr_name))


def test_desktop_event_stream_split_ready_boundary_keeps_ws_lifecycle_app_owned() -> None:
    contract = service_contract_by_id("desktop_event_stream")
    readiness = desktop_event_stream_readiness(event_bus=None, ws_server=None)

    assert contract.process_split_candidate is True
    assert contract.process_split_ready is True
    assert contract.process_adapter_kind == "ws_contract_only"
    assert contract.api_routes == ("/desktop/events/recent",)
    assert contract.runtime_facade_methods == ("desktop_events_recent",)
    assert "xinyu_desktop_events.py" in contract.contract_modules
    assert "xinyu_desktop_ws.py" in contract.contract_modules
    assert readiness.service_id == "desktop_event_stream"
    assert readiness.ready is False
    assert readiness.status == "disabled"
    assert readiness.runtime_attr == DESKTOP_EVENT_STREAM_RUNTIME_ATTR
    assert readiness.lifecycle_boundary == DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY
    assert readiness.externalization_scope == DESKTOP_EVENT_STREAM_EXTERNALIZATION_SCOPE
    assert readiness.app_owned_lifecycle is True


def test_local_not_ready_route_backend_readiness_exposes_runtime_attr_and_contract_rollback() -> None:
    backend_specs = {
        "learning_ingest": (
            "xinyu_bridge_learning_ingest_route_backend",
            "learning_ingest_route_backend_readiness",
            "LEARNING_INGEST_ROUTE_BACKEND_RUNTIME_ATTR",
        ),
        "life_metabolism": (
            "xinyu_bridge_life_metabolism_route_backend",
            "life_metabolism_route_backend_readiness",
            "LIFE_METABOLISM_ROUTE_BACKEND_RUNTIME_ATTR",
        ),
    }

    for service_id, (module_name, readiness_name, runtime_attr_name) in backend_specs.items():
        contract = service_contract_by_id(service_id)
        module = importlib.import_module(module_name)
        readiness = getattr(module, readiness_name)(SimpleNamespace())

        assert contract.process_split_candidate is False
        assert contract.process_split_ready is False
        assert readiness.service_id == service_id
        assert readiness.local_only is True
        assert readiness.ready is False
        assert readiness.runtime_attr == getattr(module, runtime_attr_name)
        assert readiness.runtime_attr.startswith("_")
        assert readiness.rollback
        assert readiness.contract_rollback
        assert readiness.rollback != readiness.contract_rollback


def test_main_runtime_and_marker_modules_remain_protected_from_process_split() -> None:
    chat = service_contract_by_id("chat_turn")
    codex = service_contract_by_id("codex_execution")

    assert chat.process_split_candidate is False
    assert chat.process_split_ready is False
    assert "xinyu_bridge_slow_live_turn.py" in chat.contract_modules
    assert codex.process_split_candidate is True
    assert codex.process_split_ready is True
    assert "xinyu_bridge_codex_runtime.py" in codex.contract_modules


def test_decision_chain_store_remains_local_state_persistence_only() -> None:
    persistence = service_contract_by_id("state_persistence")
    split_ready_modules = {
        module
        for contract in process_split_ready_contracts()
        for module in contract.contract_modules
    }

    assert persistence.process_split_candidate is False
    assert persistence.process_split_ready is False
    assert "xinyu_decision_chain_latest_store.py" in persistence.contract_modules
    assert "tests/test_decision_chain_latest_store.py" in persistence.validation_tests
    assert "xinyu_decision_chain_latest_store.py" not in split_ready_modules


def test_self_choice_store_remains_local_state_persistence_only() -> None:
    persistence = service_contract_by_id("state_persistence")
    life = service_contract_by_id("life_metabolism")
    split_ready_modules = {
        module
        for contract in process_split_ready_contracts()
        for module in contract.contract_modules
    }

    assert persistence.process_split_candidate is False
    assert persistence.process_split_ready is False
    assert life.process_split_candidate is False
    assert life.process_split_ready is False
    assert "xinyu_self_choice_store.py" in persistence.contract_modules
    assert "tests/test_self_choice_store.py" in persistence.validation_tests
    assert "xinyu_self_choice_store.py" not in split_ready_modules


def test_report_modules_have_service_owners_without_moving_stores() -> None:
    proactive = service_contract_by_id("proactive_delivery")
    learning = service_contract_by_id("learning_ingest")
    persistence = service_contract_by_id("state_persistence")

    assert "xinyu_autonomy_canary_report.py" in proactive.contract_modules
    assert "tests/test_autonomy_canary_report_store.py" in proactive.validation_tests
    assert "xinyu_proactive_response_diagnostics.py" in proactive.contract_modules
    assert "tests/test_proactive_response_diagnostics.py" in proactive.validation_tests
    assert "xinyu_proactive_lifecycle_trace.py" in proactive.contract_modules
    assert "tests/test_proactive_lifecycle_trace_store.py" in proactive.validation_tests
    assert "xinyu_autonomy_canary_report_store.py" in persistence.contract_modules
    assert "xinyu_proactive_response_diagnostics_store.py" in persistence.contract_modules
    assert "xinyu_proactive_lifecycle_trace_store.py" in persistence.contract_modules

    assert learning.process_split_candidate is False
    assert learning.process_split_ready is False
    assert "xinyu_bridge_observation_reports.py" in learning.contract_modules
    assert "tests/test_bridge_observation_reports_store.py" in learning.validation_tests
    assert "xinyu_bridge_stores.py" in persistence.contract_modules
    assert "xinyu_bridge_learning_codex_reports.py" in learning.contract_modules
    assert "tests/test_bridge_learning_codex_reports.py" in learning.validation_tests
    assert "tests/test_bridge_learning_codex_reports_store.py" in persistence.validation_tests


def test_diagnostic_reports_remain_local_without_moving_stores() -> None:
    diagnostics = service_contract_by_id("diagnostic_reports")
    persistence = service_contract_by_id("state_persistence")

    assert diagnostics.process_split_candidate is False
    assert diagnostics.process_split_ready is False
    assert diagnostics.api_routes == ()
    assert diagnostics.runtime_facade_methods == ()
    assert {
        "xinyu_module_ecology_audit.py",
        "xinyu_feedback_consumption_diagnostics.py",
        "xinyu_short_term_recall_diagnostics.py",
        "xinyu_short_term_continuity_canary.py",
        "xinyu_stage11_visual_ingress_diagnostics.py",
        "xinyu_stage11_voice_ingress_diagnostics.py",
        "xinyu_live_loop_report.py",
        "xinyu_v1_canary_readiness.py",
        "xinyu_autonomy_loop_report.py",
        "xinyu_action_openended_audit.py",
    }.issubset(diagnostics.contract_modules)
    assert {
        "tests/test_module_ecology_audit.py",
        "tests/test_feedback_consumption_diagnostics.py",
        "tests/test_short_term_recall_diagnostics.py",
        "tests/test_short_term_continuity_canary.py",
        "tests/test_stage11_visual_ingress_diagnostics.py",
        "tests/test_stage11_voice_ingress_diagnostics.py",
        "tests/test_live_loop_report.py",
        "tests/test_v1_canary_readiness.py",
        "tests/test_autonomy_loop_report.py",
        "tests/test_action_openended_audit.py",
    }.issubset(diagnostics.validation_tests)
    assert {
        "xinyu_module_ecology_audit_store.py",
        "xinyu_feedback_consumption_diagnostics_store.py",
        "xinyu_short_term_recall_diagnostics_store.py",
        "xinyu_short_term_continuity_canary_store.py",
        "xinyu_stage11_visual_ingress_diagnostics_store.py",
        "xinyu_stage11_voice_ingress_diagnostics_store.py",
        "xinyu_live_loop_report_store.py",
        "xinyu_v1_canary_readiness_store.py",
        "xinyu_autonomy_loop_report_store.py",
        "xinyu_action_openended_audit_store.py",
    }.issubset(persistence.contract_modules)


def test_memory_governance_reports_remain_local_without_moving_stores() -> None:
    memory_governance = service_contract_by_id("memory_governance_reports")
    persistence = service_contract_by_id("state_persistence")

    assert memory_governance.process_split_candidate is False
    assert memory_governance.process_split_ready is False
    assert memory_governance.api_routes == (
        "/review/inbox/command",
        "/review/goldmark/mark_request",
    )
    assert memory_governance.runtime_facade_methods == (
        "review_inbox_command",
        "goldmark_mark_request",
    )
    assert {
        "xinyu_memory_candidate_review_cli.py",
        "xinyu_memory_self_review.py",
        "xinyu_review_inbox.py",
        "xinyu_bridge_utility_review.py",
        "xinyu_bridge_utility_goldmark.py",
        "xinyu_bridge_utility_routes.py",
        "xinyu_goldmark.py",
        "xinyu_memory_health_report.py",
        "xinyu_stage8_memory_review_packet.py",
        "xinyu_stage8_duplicate_consolidation_packet.py",
        "xinyu_stage8_learning_trial_validation_packet.py",
    }.issubset(memory_governance.contract_modules)
    assert {
        "tests/test_memory_candidate_review_cli.py",
        "tests/test_memory_self_review.py",
        "tests/test_memory_review_inbox_integration.py",
        "tests/smoke/tools/xinyu_review_inbox_smoke.py",
        "tests/test_goldmark_mark.py",
        "tests/test_memory_health_report.py",
        "tests/test_stage8_memory_review_packet.py",
        "tests/test_stage8_duplicate_consolidation_packet.py",
        "tests/test_stage8_learning_trial_validation_packet.py",
    }.issubset(memory_governance.validation_tests)
    assert {
        "xinyu_memory_candidate_maintenance_store.py",
        "xinyu_memory_health_report_store.py",
        "xinyu_memory_promotion_store.py",
        "xinyu_stage8_memory_review_packet_store.py",
        "xinyu_stage8_duplicate_consolidation_packet_store.py",
        "xinyu_stage8_learning_trial_validation_packet_store.py",
        "stores/review_state.py",
    }.issubset(persistence.contract_modules)


def test_self_action_queue_store_remains_local_state_persistence_only() -> None:
    persistence = service_contract_by_id("state_persistence")
    split_ready_modules = {
        module
        for contract in process_split_ready_contracts()
        for module in contract.contract_modules
    }

    assert "stores/self_action_queue.py" in persistence.contract_modules
    assert "tests/test_self_action_queue_store.py" in persistence.validation_tests
    assert "stores/self_action_queue.py" not in split_ready_modules
