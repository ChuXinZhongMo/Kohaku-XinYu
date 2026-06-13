from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from xinyu_bridge_http_routes import post_route_requires_bridge_token
from xinyu_serviceization_contracts import ServiceBoundaryContract, service_contract_by_id


DIAGNOSTIC_REPORTS_SERVICE_ID = "diagnostic_reports"
MEMORY_GOVERNANCE_REPORTS_SERVICE_ID = "memory_governance_reports"
LOCAL_REPORT_SERVICE_MODE_LOCAL = "local_only_in_process"
LOCAL_REPORT_SERVICE_ROLLBACK = "stop_runtime_service_handle_report_builders_remain_direct"


@dataclass(frozen=True, slots=True)
class LocalReportServiceConfig:
    service_id: str
    mode: str = LOCAL_REPORT_SERVICE_MODE_LOCAL


@dataclass(frozen=True, slots=True)
class LocalReportServiceInventory:
    contract_module_count: int
    validation_test_count: int
    missing_contract_modules: tuple[str, ...]
    missing_validation_tests: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LocalReportServiceReadiness:
    service_id: str
    mode: str
    started: bool
    ready: bool
    local_only: bool
    process_split_candidate: bool
    process_split_ready: bool
    owner_layer: str
    local_owner: str
    api_routes: tuple[str, ...]
    runtime_facade_methods: tuple[str, ...]
    local_route_control_plane: bool
    control_plane_routes: tuple[str, ...]
    token_required_routes: tuple[str, ...]
    control_plane_requires_bridge_token: bool
    contract_module_count: int
    validation_test_count: int
    missing_contract_modules: tuple[str, ...]
    missing_validation_tests: tuple[str, ...]
    rollback: str
    notes: tuple[str, ...] = ()


class LocalReportServiceHandle:
    def __init__(
        self,
        config: LocalReportServiceConfig,
        *,
        repo_root: Path | None = None,
    ) -> None:
        self.config = config
        self._repo_root = _repo_root() if repo_root is None else Path(repo_root)
        self._started = False
        self._inventory: LocalReportServiceInventory | None = None

    def start(self, runtime: Any | None = None) -> LocalReportServiceReadiness:
        self._started = True
        return self.readiness(runtime)

    def close(self, runtime: Any | None = None) -> LocalReportServiceReadiness:
        self._started = False
        return self.readiness(runtime)

    def readiness(self, runtime: Any | None = None) -> LocalReportServiceReadiness:
        contract = service_contract_by_id(self.config.service_id)
        return _readiness(
            contract,
            mode=self.config.mode,
            started=self._started,
            inventory=self._contract_inventory(contract),
        )

    def _contract_inventory(self, contract: ServiceBoundaryContract) -> LocalReportServiceInventory:
        if not self._started:
            return _contract_inventory(self._repo_root, contract)
        if self._inventory is None:
            self._inventory = _contract_inventory(self._repo_root, contract)
        return self._inventory


def diagnostic_reports_service_config_from_env(env: Mapping[str, str]) -> LocalReportServiceConfig:
    return LocalReportServiceConfig(service_id=DIAGNOSTIC_REPORTS_SERVICE_ID)


def memory_governance_reports_service_config_from_env(env: Mapping[str, str]) -> LocalReportServiceConfig:
    return LocalReportServiceConfig(service_id=MEMORY_GOVERNANCE_REPORTS_SERVICE_ID)


def build_diagnostic_reports_service_handle(
    config: LocalReportServiceConfig | None = None,
    *,
    repo_root: Path | None = None,
) -> LocalReportServiceHandle:
    return LocalReportServiceHandle(
        diagnostic_reports_service_config_from_env({}) if config is None else config,
        repo_root=repo_root,
    )


def build_memory_governance_reports_service_handle(
    config: LocalReportServiceConfig | None = None,
    *,
    repo_root: Path | None = None,
) -> LocalReportServiceHandle:
    return LocalReportServiceHandle(
        memory_governance_reports_service_config_from_env({}) if config is None else config,
        repo_root=repo_root,
    )


def diagnostic_reports_service_readiness(runtime: Any) -> LocalReportServiceReadiness:
    handle = getattr(runtime, "_diagnostic_reports_service", None)
    if handle is None:
        return build_diagnostic_reports_service_handle().readiness(runtime)
    return handle.readiness(runtime)


def memory_governance_reports_service_readiness(runtime: Any) -> LocalReportServiceReadiness:
    handle = getattr(runtime, "_memory_governance_reports_service", None)
    if handle is None:
        return build_memory_governance_reports_service_handle().readiness(runtime)
    return handle.readiness(runtime)


def _readiness(
    contract: ServiceBoundaryContract,
    *,
    mode: str,
    started: bool,
    inventory: LocalReportServiceInventory,
) -> LocalReportServiceReadiness:
    missing_modules = inventory.missing_contract_modules
    missing_tests = inventory.missing_validation_tests
    ready = started and not missing_modules and not missing_tests
    control_plane_routes = contract.api_routes
    token_required_routes = tuple(
        route for route in control_plane_routes if post_route_requires_bridge_token(route)
    )
    local_route_control_plane = bool(control_plane_routes)
    control_plane_requires_bridge_token = (
        local_route_control_plane and token_required_routes == control_plane_routes
    )
    notes = [
        "local_only_report_service",
        "local_route_control_plane" if local_route_control_plane else "no_public_routes",
        "not_process_split_candidate",
    ]
    if control_plane_requires_bridge_token:
        notes.append("token_required_route_control_plane")
    return LocalReportServiceReadiness(
        service_id=contract.service_id,
        mode=mode,
        started=started,
        ready=ready,
        local_only=not contract.process_split_candidate,
        process_split_candidate=contract.process_split_candidate,
        process_split_ready=contract.process_split_ready,
        owner_layer=contract.owner_layer,
        local_owner=contract.local_owner,
        api_routes=contract.api_routes,
        runtime_facade_methods=contract.runtime_facade_methods,
        local_route_control_plane=local_route_control_plane,
        control_plane_routes=control_plane_routes,
        token_required_routes=token_required_routes,
        control_plane_requires_bridge_token=control_plane_requires_bridge_token,
        contract_module_count=inventory.contract_module_count,
        validation_test_count=inventory.validation_test_count,
        missing_contract_modules=missing_modules,
        missing_validation_tests=missing_tests,
        rollback=LOCAL_REPORT_SERVICE_ROLLBACK,
        notes=tuple(notes),
    )


def _contract_inventory(root: Path, contract: ServiceBoundaryContract) -> LocalReportServiceInventory:
    return LocalReportServiceInventory(
        contract_module_count=len(contract.contract_modules),
        validation_test_count=len(contract.validation_tests),
        missing_contract_modules=_missing_paths(root, contract.contract_modules),
        missing_validation_tests=_missing_paths(root, contract.validation_tests),
    )


def _missing_paths(root: Path, rels: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(rel for rel in rels if not (root / rel).exists())


def _repo_root() -> Path:
    return Path(__file__).resolve().parent
